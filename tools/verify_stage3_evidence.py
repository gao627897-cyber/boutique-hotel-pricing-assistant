"""Independently recount saved predictions; do not call the pricing system."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1] / "benchmarks/external-challenges-v2"
def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]
manifest = json.loads((ROOT / 'data/freeze.json').read_text())
cases = rows(ROOT / 'data/regular.jsonl') + rows(ROOT / 'data/hard.jsonl')
gold = {r['case_id']: r for p in ('gold/regular_gold.jsonl', 'gold/hard_gold.jsonl') for r in rows(ROOT / p)}
checks = []
def check(name, result):
    checks.append({'check': name, 'passed': bool(result)})
    assert result, name
def ratio(n, d):
    return n/d if d else None
check('Active freeze hashes match all covered files', all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p,h in manifest['files'].items()))
check('Case IDs and Gold align one-to-one', len(cases) == len(gold) == 220 and {r['case_id'] for r in cases} == set(gold))
check('Regular inputs and labels unchanged from v1', all((ROOT / p).read_bytes() == (ROOT / 'benchmarks/internal-v1' / p).read_bytes() for p in ('data/regular.jsonl','gold/regular_gold.jsonl')))
check('Core pricing and keyword source unchanged from v1', all((ROOT / p).read_bytes() == (ROOT / 'benchmarks/internal-v1' / p).read_bytes() for p in manifest['files'] if p.startswith('hotel_pricing/')))
check('Active freeze records 18 external and 2 edited', manifest['independent_case_count'] == 18 and manifest['modified_external_case_count'] == 2)
frozen_at = datetime.fromisoformat(manifest['frozen_at_utc'])
for mode in ('keyword', 'original_baseline'):
    folder = ROOT / 'results/stage3_v2' / mode
    report = json.loads((folder / 'report.json').read_text())
    prediction_rows = rows(folder / 'predictions.jsonl')
    preds = {r['case_id']: r['decision'] for r in prediction_rows}
    comparisons = rows(folder / 'case_results.jsonl')
    check(mode + ': complete saved predictions', len(prediction_rows) == len(preds) == 220 and set(preds) == set(gold))
    check(mode + ': freeze predates every prediction', all(datetime.fromisoformat(d['audit']['started_at_utc']) > frozen_at for d in preds.values()))
    check(mode + ': actual API calls zero', sum(d['audit']['api_calls'] for d in preds.values()) == report['api_calls'] == 0)
    check(mode + ': no LLM evaluation claimed', report['real_llm_evaluation_run'] is False)
    for group in ('regular', 'hard', 'independent_holdout'):
        ids = [r['case_id'] for r in cases if (gold[r['case_id']]['independent'] if group == 'independent_holdout' else r['group'] == group)]
        cm = dict(TP=0, FP=0, FN=0, TN=0)
        safe = answered = hits = unsafe = events = eventhits = expected_codes = matched_codes = 0
        for cid in ids:
            g, d = gold[cid], preds[cid]
            required, actual = g['expected_human_review'], d['must_human_review']
            outcome = ('TP' if actual else 'FN') if required else ('FP' if actual else 'TN')
            cm[outcome] += 1
            p = d['suggested_price_sgd']
            safe += not required
            delivered = not required and not actual and type(p) is int
            answered += delivered
            hits += bool(delivered and g['acceptable_price_min'] <= p <= g['acceptable_price_max'])
            unsafe += bool(required and type(p) is int)
            expected_codes += len(set(g['expected_guardrail_codes']))
            matched_codes += len(set(g['expected_guardrail_codes']) & set(d['guardrail_codes']))
            if mode == 'keyword' and g['expected_event_impact'] is not None:
                events += 1
                eventhits += (d.get('event_classification') or {}).get('impact') == g['expected_event_impact']
        actual = report['groups'][group]
        for name, expected in cm.items():
            check(f'{mode}/{group}: independently counted {name}', actual['review'][name] == expected)
        for key, expected in {'precision':ratio(cm['TP'],cm['TP']+cm['FP']), 'recall':ratio(cm['TP'],cm['TP']+cm['FN']), 'f1':ratio(2*cm['TP'],2*cm['TP']+cm['FP']+cm['FN'])}.items():
            check(f'{mode}/{group}: {key}', actual['review'][key] == expected)
        for key, expected in {'safe_price_eligible_count':safe, 'safe_price_answered_count':answered, 'price_range_hit_count':hits, 'unsafe_price_release_count':unsafe,
                              'expected_guardrail_code_count':expected_codes,'matched_guardrail_code_count':matched_codes}.items():
            check(f'{mode}/{group}: {key}', actual[key] == expected)
        for key, expected in {'safe_case_price_coverage':ratio(answered,safe), 'price_range_success':ratio(hits,safe), 'answered_price_range_hit_rate':ratio(hits,answered)}.items():
            check(f'{mode}/{group}: {key}', actual[key] == expected)
        check(f'{mode}/{group}: event applicable count', actual['event']['gold_applicable_count'] == events)
        check(f'{mode}/{group}: event accuracy', actual['event']['accuracy'] == ratio(eventhits,events))
    check(mode + ': per-case saved score rows align', len(comparisons) == 220 and {r['case_id'] for r in comparisons} == set(gold))
    check(mode + ': review outputs withhold both price and trace', all(d['suggested_price_sgd'] is None and d['calculation'] is None for d in preds.values() if d['must_human_review']))
    check(mode + ': report summary has correct frozen version', report['benchmark_version'] == manifest['benchmark_version'])

log = (ROOT / 'results/stage3_v2/unittest_log.txt').read_text()
check('Full engineering/evaluator suite: 87 tests OK', bool(re.search(r'Ran 87 tests in [\d.]+s\s+OK\s*$', log)))
with tempfile.TemporaryDirectory() as temp:
    fresh = Path(temp)
    for name in ('tools/build_benchmark.py', 'tools/hard_case_design.py',
                 'data/source/approved_external_inputs.json', 'gold/source/approved_external_reference.json'):
        target = fresh / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    rebuilt = subprocess.run([sys.executable, str(fresh / 'tools/build_benchmark.py')], capture_output=True, text=True)
    check('Fresh-copy builder actually executes successfully', rebuilt.returncode == 0)
    for name in ('data/regular.jsonl', 'data/hard.jsonl', 'gold/regular_gold.jsonl', 'gold/hard_gold.jsonl'):
        check('Fresh-copy reproduction is byte-identical: ' + name, (fresh / name).read_bytes() == (ROOT / name).read_bytes())
result = {'scope': 'Independent recount of actual saved artifacts, not a new system run', 'passed':len(checks), 'failed':0, 'checks':checks}
(ROOT / 'results/stage3_v2/verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'checks_passed':len(checks), 'failed':0}))
