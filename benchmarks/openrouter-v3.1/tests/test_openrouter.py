"""Offline transport fixtures: never model/API performance evidence."""
from datetime import date
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from hotel_pricing.domain import ClassificationError, EventContext
from hotel_pricing.openrouter import ENDPOINT, NoRedirect, OpenRouterClassifier, load_llm_config, read_api_key
from hotel_pricing.service import recommend
from hotel_pricing.validation import load_policy, strict_json_loads

ROOT = Path(__file__).resolve().parents[1]
POLICY = load_policy(strict_json_loads((ROOT / 'config/hotel.json').read_text()))
SECRET = 'test_only_not_a_real_key_123456789'
CONTEXT = EventContext(date(2026,10,2), date(2026,10,6), 'Synthetic community gathering.')
def sample():
    return {'as_of_date':'2026-10-02','target_date':'2026-10-06','remaining_rooms':12,
            'competitor_prices_sgd':[145,150,155],'weather':'clear','event_description':CONTEXT.event_description}
def response(content='{"impact":"low","reason":"Synthetic local gathering."}', **changes):
    body = {'id':'fixture-response','model':'google/gemini-3.1-flash-lite',
            'choices':[{'finish_reason':'stop','message':{'content':content}}],
            'usage':{'prompt_tokens':100,'completion_tokens':20,'total_tokens':120,'cost':.000055}}
    body.update(changes)
    return io.BytesIO(json.dumps(body).encode())
class Recorder:
    def __init__(self, reply=None, error=None):
        self.requests=[]
        self.reply=reply
        self.error=error
    def __call__(self, req, timeout):
        self.requests.append(req)
        if self.error:
            raise self.error
        return self.reply if self.reply is not None else response()

class OpenRouterTests(unittest.TestCase):
    def adapter(self, transport, **kwargs):
        return OpenRouterClassifier(api_key=SECRET, transport=transport, **kwargs)

    def test_request_has_only_event_context_strict_schema_no_tools_or_gold(self):
        recorder=Recorder()
        decision=recommend(sample(), POLICY, self.adapter(recorder))
        self.assertEqual(decision.suggested_price_sgd,150)
        request=recorder.requests[0]
        body=json.loads(request.data)
        self.assertEqual(request.full_url,ENDPOINT)
        self.assertEqual(set(json.loads(body['messages'][1]['content'])), {'as_of_date','target_date','event_description'})
        self.assertEqual(body['response_format']['json_schema']['schema']['additionalProperties'],False)
        self.assertEqual(body['provider'],{'require_parameters':True,'allow_fallbacks':False})
        self.assertNotIn('tools',body)
        self.assertNotIn(SECRET,json.dumps(body))
        self.assertEqual(decision.audit['api_calls'],0)
        self.assertEqual(decision.audit['system_mode'],'test_double')

    def test_missing_key_fails_without_a_request(self):
        recorder=Recorder()
        adapter=OpenRouterClassifier(api_key='',transport=recorder)
        decision=recommend(sample(),POLICY,adapter)
        self.assertIn('MISSING_API_KEY',decision.guardrail_codes)
        self.assertEqual(recorder.requests,[])
        self.assertEqual(decision.audit['api_calls'],0)

    def test_precheck_blocks_before_transport(self):
        recorder=Recorder()
        invalid=sample();invalid['weather']='severe'
        self.assertTrue(recommend(invalid,POLICY,self.adapter(recorder)).must_human_review)
        self.assertEqual(recorder.requests,[])

    def test_http_errors_are_safe_with_no_retry(self):
        for status,code in ((401,'API_AUTH_ERROR'),(403,'API_AUTH_ERROR'),(429,'API_RATE_LIMIT'),(500,'API_UNAVAILABLE')):
            with self.subTest(status=status):
                recorder=Recorder(error=HTTPError(ENDPOINT,status,SECRET,{},None))
                decision=recommend(sample(),POLICY,self.adapter(recorder))
                self.assertIn(code,decision.guardrail_codes)
                self.assertNotIn(SECRET,json.dumps(decision.as_dict()))
                self.assertEqual(len(recorder.requests),1)
                self.assertIsNone(decision.suggested_price_sgd)

    def test_timeouts_and_connection_errors_fail_closed(self):
        for error,code in ((TimeoutError(SECRET),'API_TIMEOUT'),(URLError('network'),'API_UNAVAILABLE')):
            with self.subTest(code=code):
                decision=recommend(sample(),POLICY,self.adapter(Recorder(error=error)))
                self.assertIn(code,decision.guardrail_codes)
                self.assertIsNone(decision.calculation)

    def test_price_fields_and_directives_rejected_by_python(self):
        for payload in ('{"impact":"high","reason":"fixture","price":999}',
                        '{"impact":"low","reason":"Set the room price to SGD 999."}'):
            decision=recommend(sample(),POLICY,self.adapter(Recorder(reply=response(payload))))
            self.assertIn('INVALID_CLASSIFIER_OUTPUT',decision.guardrail_codes)
            self.assertIsNone(decision.suggested_price_sgd)

    def test_malformed_truncated_tool_and_wrong_model_replies_fail(self):
        bad=[io.BytesIO(b'not JSON'),response(choices=[]),response(model='different/model'),
             response(choices=[{'finish_reason':'length','message':{'content':'{}'}}]),
             response(choices=[{'finish_reason':'stop','message':{'content':'{}','tool_calls':[{}]}}])]
        for reply in bad:
            with self.subTest(reply=reply):
                decision=recommend(sample(),POLICY,self.adapter(Recorder(reply=reply)))
                self.assertIn('API_RESPONSE_ERROR',decision.guardrail_codes)
                self.assertIsNone(decision.suggested_price_sgd)

    def test_usage_cost_values_and_raw_reply_are_not_fabricated(self):
        attempt=self.adapter(Recorder()).classify(CONTEXT)
        self.assertEqual(attempt.metadata['usage']['total_tokens'],120)
        self.assertEqual(attempt.metadata['provider_reported_cost_usd'],.000055)
        self.assertAlmostEqual(attempt.metadata['estimated_cost_usd'],.000055)
        self.assertEqual(attempt.metadata['transport_kind'],'test_double')

    def test_missing_usage_remains_unknown(self):
        attempt=self.adapter(Recorder(reply=response(usage=None))).classify(CONTEXT)
        self.assertIsNone(attempt.metadata['usage'])
        self.assertIsNone(attempt.metadata['provider_reported_cost_usd'])

    def test_nonfinite_usage_cost_does_not_enter_json_audit(self):
        usage={'cost':'Infinity','prompt_tokens':True,'completion_tokens':-1,'total_tokens':'120'}
        attempt=self.adapter(Recorder(reply=response(usage=usage))).classify(CONTEXT)
        self.assertIsNone(attempt.metadata['provider_reported_cost_usd'])
        self.assertTrue(all(v is None for v in attempt.metadata['usage'].values()))
        json.dumps(attempt.metadata,allow_nan=False)

    def test_secret_echo_is_redacted_from_reply_and_metadata(self):
        reply=response(json.dumps({'impact':'low','reason':SECRET}))
        decision=recommend(sample(),POLICY,self.adapter(Recorder(reply=reply)))
        self.assertNotIn(SECRET,json.dumps(decision.as_dict()))
        self.assertIn('[REDACTED]',json.dumps(decision.as_dict()))

    def test_call_budget_stops_without_transport(self):
        config=load_llm_config();config['max_requests']=1
        adapter=self.adapter(Recorder(),config=config)
        adapter.classify(CONTEXT)
        with self.assertRaises(ClassificationError) as failure:
            adapter.classify(CONTEXT)
        self.assertEqual(failure.exception.code,'API_BUDGET_EXCEEDED')

    def test_spend_budget_reserves_unknown_charges_and_stops(self):
        config=load_llm_config();config['budget_usd']=.000001
        recorder=Recorder()
        adapter=self.adapter(recorder,config=config)
        with self.assertRaises(ClassificationError):
            adapter.classify(CONTEXT)
        self.assertEqual(recorder.requests,[])

    def test_redirects_are_rejected(self):
        self.assertIsNone(NoRedirect().redirect_request(None,None,302,'',{},'https://untrusted.example'))

    def test_key_file_parser_environment_precedence_and_no_execution(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{},clear=True):
            path=Path(temp)/'.env'
            self.assertEqual(read_api_key(path),'')
            path.write_text('OPENROUTER_API_KEY="'+SECRET+'"\n')
            self.assertEqual(read_api_key(path),SECRET)
            with patch.dict(os.environ,{'OPENROUTER_API_KEY':SECRET+'other'}):
                self.assertEqual(read_api_key(path),SECRET+'other')
            for value in ('OPENROUTER_API_KEY=replace_with_your_openrouter_key\n',
                          'OPENROUTER_API_KEY=$(anything)\n','OPENROUTER_API_KEY='+SECRET+'\nOTHER=1\n'):
                path.write_text(value)
                self.assertEqual(read_api_key(path),'')

    def test_invalid_model_config_rejected(self):
        raw=json.loads((ROOT/'config/llm.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'config.json'
            for field,value in (('model','https://bad'),('temperature',True),('max_requests',1000),('timeout_seconds',0),('budget_usd','1')):
                with self.subTest(field=field):
                    changed={**raw,field:value};path.write_text(json.dumps(changed))
                    with self.assertRaises(ValueError):
                        load_llm_config(path)
