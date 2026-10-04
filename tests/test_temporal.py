"""Synthetic temporal regressions; no genuine model outputs or API calls."""
from datetime import date
import io
import json
from pathlib import Path
import unittest

from hotel_pricing.domain import EventContext
from hotel_pricing.openrouter import OpenRouterClassifier
from hotel_pricing.service import recommend
from hotel_pricing.temporal import validate_temporal_payload
from hotel_pricing.validation import load_policy, strict_json_loads

ROOT = Path(__file__).resolve().parents[1]
POLICY = load_policy(strict_json_loads((ROOT / 'config/hotel.json').read_text()))

def context(text, decision='2026-03-02', stay='2026-03-16'):
    return EventContext(date.fromisoformat(decision), date.fromisoformat(stay), text)

def payload(notices=None):
    return {'impact': 'low', 'reason': 'Synthetic event status.',
            'dated_notices': [] if notices is None else notices}

def notice(stamp, quote):
    return {'date': stamp, 'quote': quote}

class TemporalTests(unittest.TestCase):
    def test_future_status_blocks_even_when_model_says_low_and_stay_is_later(self):
        quote = 'was officially cancelled on 8 March'
        result, evidence = validate_temporal_payload(payload([notice('2026-03-08', quote)]), context(quote))
        self.assertEqual(result['impact'], 'uncertain')
        self.assertEqual(evidence['model_impact'], 'low')
        self.assertTrue(evidence['python_temporal_block'])

    def test_before_and_same_day_notices_remain_usable(self):
        for stamp in ('2026-03-01', '2026-03-02'):
            quote = 'Cancellation confirmed on ' + stamp
            with self.subTest(stamp=stamp):
                result, evidence = validate_temporal_payload(payload([notice(stamp, quote)]), context(quote))
                self.assertEqual(result['impact'], 'low')
                self.assertFalse(evidence['python_temporal_block'])

    def test_future_event_date_without_status_notice_does_not_block(self):
        result, evidence = validate_temporal_payload(payload(), context('The local fair will take place on 16 March.'))
        self.assertEqual(result['impact'], 'low')
        self.assertEqual(evidence['dated_notices'], [])

    def test_undated_cancellation_does_not_get_an_invented_notice_date(self):
        result, _ = validate_temporal_payload(payload(), context('The festival has been cancelled.'))
        self.assertEqual(result['impact'], 'low')

    def test_multiple_notices_keep_future_and_past_evidence(self):
        first, second = 'Confirmed on 1 March 2026', 'Updated on March 8, 2026'
        result, evidence = validate_temporal_payload(payload([
            notice('2026-03-01', first), notice('2026-03-08', second)]), context(first + '. ' + second))
        self.assertEqual(result['impact'], 'uncertain')
        self.assertEqual(len(evidence['dated_notices']), 2)

    def test_explicit_year_supports_year_boundary(self):
        quote = 'Official notice posted on January 2, 2027'
        result, _ = validate_temporal_payload(payload([notice('2027-01-02', quote)]),
            context(quote, '2026-12-28', '2027-01-05'))
        self.assertEqual(result['impact'], 'uncertain')

    def test_omitted_year_at_year_boundary_is_rejected(self):
        quote = 'Official notice posted on January 2'
        with self.assertRaises(ValueError):
            validate_temporal_payload(payload([notice('2027-01-02', quote)]),
                context(quote, '2026-12-28', '2027-01-05'))

    def test_fabricated_excerpt_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_temporal_payload(payload([notice('2026-03-08', 'Cancelled on 8 March')]),
                context('No known cancellation.'))

    def test_date_mismatch_and_invalid_calendar_dates_are_rejected(self):
        quote = 'Cancelled on 8 March 2026'
        for stamp in ('2026-03-07', '2025-03-08', '2026-02-30', '8 March'):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                validate_temporal_payload(payload([notice(stamp, quote)]), context(quote))

    def test_protocol_limits_missing_fields_extra_fields_and_duplicates(self):
        quote = 'Cancelled on 8 March'
        item = notice('2026-03-08', quote)
        bad = [payload([item, item]), payload([item] * 9), payload('not a list'),
               {'impact': 'low', 'reason': 'fixture'},
               {**payload(), 'price': 150}, payload([{'date': '2026-03-08', 'quote': quote, 'price': 300}])]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_temporal_payload(value, context(quote))

    def test_service_withholds_price_when_raw_model_label_is_definite(self):
        quote = 'Cancellation confirmed on 8 March'
        content = json.dumps(payload([notice('2026-03-08', quote)]))
        transport = lambda request, timeout: io.BytesIO(json.dumps({
            'id': 'synthetic-temporal-fixture', 'model': 'google/gemini-3.1-flash-lite',
            'choices': [{'finish_reason': 'stop', 'message': {'content': content}}]}).encode())
        adapter = OpenRouterClassifier(api_key='synthetic_test_key_not_real_12345', transport=transport)
        result = recommend({'as_of_date': '2026-03-02', 'target_date': '2026-03-16',
            'remaining_rooms': 12, 'competitor_prices_sgd': [145, 150, 155],
            'weather': 'clear', 'event_description': quote}, POLICY, adapter)
        self.assertEqual(result.guardrail_codes, ['EVENT_UNCERTAIN'])
        self.assertIsNone(result.suggested_price_sgd)
        self.assertIsNone(result.calculation)
        self.assertEqual(result.audit['api_calls'], 0)
        self.assertTrue(result.audit['classification_metadata']['temporal_evidence']['python_temporal_block'])

    def test_unsubstantiated_extraction_fails_closed_through_service(self):
        content = json.dumps(payload([notice('2026-03-08', 'Invented quote on 8 March')]))
        transport = lambda request, timeout: io.BytesIO(json.dumps({
            'id': 'synthetic-bad-quote', 'model': 'google/gemini-3.1-flash-lite',
            'choices': [{'finish_reason': 'stop', 'message': {'content': content}}]}).encode())
        adapter = OpenRouterClassifier(api_key='synthetic_test_key_not_real_12345', transport=transport)
        result = recommend({'as_of_date': '2026-03-02', 'target_date': '2026-03-16',
            'remaining_rooms': 12, 'competitor_prices_sgd': [145, 150, 155],
            'weather': 'clear', 'event_description': 'A small local event.'}, POLICY, adapter)
        self.assertIn('INVALID_CLASSIFIER_OUTPUT', result.guardrail_codes)
        self.assertIsNone(result.suggested_price_sgd)
        self.assertEqual(result.audit['api_calls'], 0)
