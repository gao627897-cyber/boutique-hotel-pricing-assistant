"""Load the owner-approved external challenge source without running a model.

Original IDs, authorship and the two approved edits are in data/provenance.json.
Historical assistant-authored cases live under benchmarks/internal-v1.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def hard_cases():
    cases = json.loads((ROOT / "data/source/approved_external_inputs.json").read_text())
    gold = json.loads((ROOT / "gold/source/approved_external_reference.json").read_text())
    return cases, gold
