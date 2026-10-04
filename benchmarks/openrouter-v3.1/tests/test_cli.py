"""Run the actual CLI in subprocesses; all fixtures are synthetic/test-only."""

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "hotel_pricing", *args],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )

    def test_json_normal_real_cli(self):
        result = self.run_cli("--input", "examples/normal.json", "--format", "json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["suggested_price_sgd"], 150)
        self.assertEqual(data["audit"]["api_calls"], 0)
        self.assertEqual(data["audit"]["system_mode"], "non_ai_baseline")

    def test_text_output_explains_python_formula(self):
        result = self.run_cli("--input", "examples/weekend_scarcity.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SGD 195", result.stdout)
        self.assertIn("Python formula:", result.stdout)
        self.assertIn("API calls: 0", result.stdout)

    def test_all_review_examples_have_null_price(self):
        for name, code in [
            ("review_conflict", "SIGNAL_CONFLICT"),
            ("review_missing_weather", "MISSING_FIELD"),
            ("review_uncertain", "EVENT_UNCERTAIN"),
        ]:
            with self.subTest(name=name):
                result = self.run_cli("--input", f"examples/{name}.json", "--format", "json")
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads(result.stdout)
                self.assertEqual(data["status"], "human_review")
                self.assertIsNone(data["suggested_price_sgd"])
                self.assertIn(code, data["guardrail_codes"])

    def test_unavailable_mode_real_cli(self):
        result = self.run_cli("--input", "examples/normal.json", "--classifier", "unavailable", "--format", "json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "human_review")
        self.assertIsNone(data["suggested_price_sgd"])
        self.assertFalse(data["audit"]["api_called"])

    def test_original_baseline_real_cli(self):
        result = self.run_cli("--input", "examples/weekend_scarcity.json", "--strategy", "original_baseline", "--format", "json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["suggested_price_sgd"], 165)

    def test_invalid_json_duplicate_keys_and_nonfinite(self):
        for text in ('{"x":}', '{"weather":"clear","weather":"severe"}', '{"quote":NaN}', '{"quote":Infinity}', '{"quote":1e9999999999999999999}'):
            with self.subTest(text=text):
                with tempfile.TemporaryDirectory() as temp:
                    path = Path(temp) / "bad.json"
                    path.write_text(text)
                    result = self.run_cli("--input", str(path), "--format", "json")
                    self.assertEqual(result.returncode, 2, result.stderr)
                    data = json.loads(result.stdout)
                    self.assertEqual(data["guardrail_codes"], ["INPUT_FILE_ERROR"])
                    self.assertIsNone(data["suggested_price_sgd"])

    def test_extreme_but_finite_json_number_is_data_review_not_parse_error(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "extreme_quote.json"
            text = (ROOT / "examples/normal.json").read_text().replace(
                "[145, 150, 155]", "[1e999999999999999999, 150, 155]"
            )
            path.write_text(text)
            result = self.run_cli("--input", str(path), "--format", "json")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["status"], "human_review")
            self.assertIn("COMPETITOR_PRICE_OUT_OF_RANGE", data["guardrail_codes"])
            self.assertIsNone(data["suggested_price_sgd"])

    def test_nonexistent_file_returns_review_json_without_traceback(self):
        result = self.run_cli("--input", "examples/does_not_exist.json", "--format", "json")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["guardrail_codes"], ["INPUT_FILE_ERROR"])
        self.assertNotIn("Traceback", result.stderr)

    def test_unpaired_unicode_json_is_safe_parse_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad_unicode.json"
            path.write_text('{"event_description": "\\ud800"}')
            result = self.run_cli("--input", str(path), "--format", "json")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["guardrail_codes"], ["INPUT_FILE_ERROR"])
            self.assertNotIn("Traceback", result.stderr)

    def test_invalid_configuration_stops_before_classification(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad_config.json"
            path.write_text("{}")
            result = self.run_cli("--input", "examples/normal.json", "--config", str(path), "--format", "json")
            self.assertEqual(result.returncode, 2)
            data = json.loads(result.stdout)
            self.assertEqual(data["guardrail_codes"], ["CONFIG_ERROR"])
            self.assertFalse(data["audit"]["classifier_invoked"])

    def test_write_actual_output_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "nested" / "run.json"
            result = self.run_cli("--input", "examples/normal.json", "--format", "json", "--output", str(path))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(path.read_text()), json.loads(result.stdout))
            original = path.read_bytes()
            again = self.run_cli("--input", "examples/weekend_scarcity.json", "--output", str(path))
            self.assertEqual(again.returncode, 2)
            self.assertEqual(path.read_bytes(), original)

    def test_absolute_input_and_default_config_work_from_other_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            # Use PYTHONPATH only in this portability test, not in the project.
            import os
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(ROOT)
            result = subprocess.run(
                [sys.executable, "-m", "hotel_pricing", "--input", str(ROOT / "examples/normal.json"), "--format", "json"],
                cwd=temp, env=environment, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["suggested_price_sgd"], 150)
