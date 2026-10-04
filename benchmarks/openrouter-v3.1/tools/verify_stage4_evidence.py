"""Independently recount real saved results. Never invoke an API or model."""
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]
def ratio(n,d):
    return n/d if d else None
checks=[]
def check(name, passed):
    checks.append({'check':name,'passed':bool(passed)})
    if not passed:
        raise AssertionError(name)

manifest=json.loads((ROOT/'data/freeze.json').read_text())
frozen=datetime.fromisoformat(manifest['frozen_at_utc'])
check('Current execution hashes match frozen sources',all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in manifest['files'].items()))
cases=read_rows(ROOT/'data/regular.jsonl')+read_rows(ROOT/'data/hard.jsonl')
gold={r['case_id']:r for name in ('gold/regular_gold.jsonl','gold/hard_gold.jsonl') for r in read_rows(ROOT/name)}
check('220 one-to-one case/Gold identifiers',len(cases)==len(gold)==220 and {r['case_id'] for r in cases}==set(gold))
archive=ROOT/'benchmarks/external-challenges-v2'
for path in ('data/regular.jsonl','data/hard.jsonl','gold/regular_gold.jsonl','gold/hard_gold.jsonl','config/hotel.json','hotel_pricing/pricing.py','hotel_pricing/validation.py','hotel_pricing/classifiers.py'):
    check('Stage-3 approved data/numerical logic unchanged: '+path,(ROOT/path).read_bytes()==(archive/path).read_bytes())

for mode,folder in (('keyword','keyword'),('original_baseline','original_baseline'),('openrouter','openrouter_run_01')):
    directory=ROOT/'results/stage4'/folder
    report=json.loads((directory/'report.json').read_text())
    saved=read_rows(directory/'predictions.jsonl')
    pi={r['case_id']:r['decision'] for r in saved}
    check(mode+': complete saved results',len(saved)==len(pi)==220 and set(pi)==set(gold))
    check(mode+': execution version recorded',report['execution_version']==manifest['execution_version'])
    check(mode+': Gold freeze predates every decision',all(datetime.fromisoformat(p['audit']['started_at_utc'])>frozen for p in pi.values()))
    actual_calls=sum(p['audit']['api_calls'] for p in pi.values())
    check(mode+': report/API counts agree',actual_calls==report['api_calls'])
    check(mode+': schema invariants checked independently',all((p['status']=='human_review')==p['must_human_review'] and (p['suggested_price_sgd'] is None and p['calculation'] is None if p['must_human_review'] else type(p['suggested_price_sgd']) is int and 80<=p['suggested_price_sgd']<=300 and p['calculation'] is not None) for p in pi.values()))
    for group in ('regular','hard','independent_holdout'):
        subset=[r['case_id'] for r in cases if (gold[r['case_id']]['independent'] if group=='independent_holdout' else r['group']==group)]
        cm={'TP':0,'FP':0,'FN':0,'TN':0}
        safe=answered=hits=unsafe=expected_codes=matched_codes=reviews=events=event_hits=0
        for identifier in subset:
            g,p=gold[identifier],pi[identifier]
            required,actual=g['expected_human_review'],p['must_human_review']
            cm[('TP' if actual else 'FN') if required else ('FP' if actual else 'TN')]+=1
            reviews+=actual
            price=p['suggested_price_sgd']
            safe+=not required
            emitted=not required and not actual and type(price) is int
            answered+=emitted
            hits+=bool(emitted and g['acceptable_price_min']<=price<=g['acceptable_price_max'])
            unsafe+=bool(required and type(price) is int)
            expected_codes+=len(set(g['expected_guardrail_codes']))
            matched_codes+=len(set(g['expected_guardrail_codes'])&set(p['guardrail_codes']))
            if mode!='original_baseline' and g['expected_event_impact'] is not None:
                events+=1
                event_hits+=(p.get('event_classification') or {}).get('impact')==g['expected_event_impact']
        measured=report['groups'][group]
        for field,value in cm.items():
            check(f'{mode}/{group}: {field}',measured['review'][field]==value)
        for field,value in {'precision':ratio(cm['TP'],cm['TP']+cm['FP']),'recall':ratio(cm['TP'],cm['TP']+cm['FN']),'f1':ratio(2*cm['TP'],2*cm['TP']+cm['FP']+cm['FN'])}.items():
            check(f'{mode}/{group}: {field}',measured['review'][field]==value)
        values={'case_count':len(subset),'review_rate':ratio(reviews,len(subset)),
                'safe_price_eligible_count':safe,'safe_price_answered_count':answered,
                'price_range_hit_count':hits,'unsafe_price_release_count':unsafe,
                'expected_guardrail_code_count':expected_codes,'matched_guardrail_code_count':matched_codes,
                'safe_case_price_coverage':ratio(answered,safe),'price_range_success':ratio(hits,safe),
                'answered_price_range_hit_rate':ratio(hits,answered)}
        for field,value in values.items():
            check(f'{mode}/{group}: {field}',measured[field]==value)
        check(f'{mode}/{group}: event denominator',measured['event']['gold_applicable_count']==events)
        check(f'{mode}/{group}: event accuracy',measured['event']['accuracy']==ratio(event_hits,events))
    if mode=='openrouter':
        called=[p for p in pi.values() if p['audit']['api_calls']]
        metadata=[p['audit']['classification_metadata'] for p in called]
        ids=[m.get('response_id') for m in metadata if m.get('response_id')]
        check('LLM: 210 real request attempts; ten precheck skips',actual_calls==210 and len(called)==210 and len(saved)-len(called)==10)
        check('LLM: actual HTTPS evidence, not test doubles',all(p['audit']['system_mode']=='llm' and p['audit']['classification_metadata']['transport_kind']=='actual_https_request' for p in called))
        check('LLM: no retries were silently performed',all(m['automatic_retries']==0 for m in metadata))
        check('LLM: returned response IDs have no duplicates',len(ids)==len(set(ids)))
        check('LLM: actual replies came from the frozen requested model',all(m.get('returned_model')==m['requested_model'] for m in metadata if m.get('model_reply') is not None))
        u=report['provider_usage']
        for field in ('prompt_tokens','completion_tokens','total_tokens'):
            tokens=[(m.get('usage') or {}).get(field) for m in metadata]
            check('LLM: '+field+' sum',u[field+'_known_subtotal']==sum(t for t in tokens if type(t) is int))
            check('LLM: '+field+' missing count',u[field+'_missing_request_count']==sum(type(t) is not int for t in tokens))
        costs=[m.get('provider_reported_cost_usd') for m in metadata]
        check('LLM: reported cost subtotal',math.isclose(u['known_reported_cost_subtotal_usd'],sum(c for c in costs if c is not None),abs_tol=1e-12))
        check('LLM: missing cost count',u['missing_reported_cost_request_count']==sum(c is None for c in costs))
        check('LLM: real evaluation identified',report['real_llm_evaluation_run'] is True)
    else:
        check(mode+': no model calls or fabricated LLM score',actual_calls==0 and report['real_llm_evaluation_run'] is False)

execution=json.loads((ROOT/'results/stage4/openrouter_run_01_execution.json').read_text())
check('Real evaluation command exited successfully',execution['exit_code']==0)
log=(ROOT/'results/stage4_preflight/unittest_log.txt').read_text()
check('103 offline tests actually passed',bool(re.search(r'Ran 103 tests in [\d.]+s\s+OK\s*$',log)))
result={'scope':'Independent recount of actual saved results; zero new API calls','passed':len(checks),'failed':0,'checks':checks}
(ROOT/'results/stage4/verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':len(checks),'failed':0}))
