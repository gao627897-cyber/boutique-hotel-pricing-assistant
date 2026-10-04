"""Ground dated status notices and compare knowledge time in deterministic code.

The LLM extracts notices from untrusted text; this module checks exact quotes,
calendar dates and the decision-time boundary. Event occurrence dates are not
knowledge dates. Missing extraction remains a semantic limitation, not proof
that the text contains no later evidence. Supported date forms are ISO dates
and English month names; ambiguous cross-year dates fail closed.
"""
from datetime import date
import re

from .validation import strict_json_loads, validate_event_output

MONTHS = {name: number for number, names in enumerate((
    ('jan', 'january'), ('feb', 'february'), ('mar', 'march'), ('apr', 'april'),
    ('may',), ('jun', 'june'), ('jul', 'july'), ('aug', 'august'),
    ('sep', 'sept', 'september'), ('oct', 'october'), ('nov', 'november'),
    ('dec', 'december')), 1) for name in names}
MONTH_PATTERN = '|'.join(sorted(MONTHS, key=len, reverse=True))
DAY_FIRST = re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(' + MONTH_PATTERN + r')\.?\b(?:\s*,?\s*(\d{4}))?', re.I)
MONTH_FIRST = re.compile(r'\b(' + MONTH_PATTERN + r')\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b(?:\s*,?\s*(\d{4}))?', re.I)


def quoted_dates(quote, context):
    """Only corroborate stated dates; never derive evidence from the stay date."""
    result = set()
    for token in re.findall(r'(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)', quote):
        result.add(date.fromisoformat(token))
    for pattern, month_first in ((DAY_FIRST, False), (MONTH_FIRST, True)):
        for match in pattern.finditer(quote):
            month = MONTHS[match.group(1 if month_first else 2).lower()]
            day = int(match.group(2 if month_first else 1))
            year_text = match.group(3)
            if year_text is None and context.as_of_date.year != context.target_date.year:
                raise ValueError('Unqualified cross-year notice date is ambiguous.')
            year = int(year_text) if year_text else context.as_of_date.year
            result.add(date(year, month, day))
    return result


def validate_temporal_payload(payload, context):
    """Return the two-field event signal plus auditable Python temporal evidence.

Protocol/grounding errors are rejected. Grounded future knowledge overrides
any proposed impact with uncertain; numerical pricing never sees that label.
"""
    value = strict_json_loads(payload) if isinstance(payload, str) else payload
    if not isinstance(value, dict) or set(value) != {'impact', 'reason', 'dated_notices'}:
        raise ValueError('Activity response must contain exactly three fields.')
    signal, issues = validate_event_output({k: value[k] for k in ('impact', 'reason')})
    if issues:
        raise ValueError('Invalid activity signal.')
    notices = value['dated_notices']
    if not isinstance(notices, list) or len(notices) > 8:
        raise ValueError('Invalid dated-notice list.')
    seen = set()
    checked = []
    for notice in notices:
        if not isinstance(notice, dict) or set(notice) != {'date', 'quote'}:
            raise ValueError('Invalid dated-notice structure.')
        text, stamp = notice['quote'], notice['date']
        if (not isinstance(text, str) or not 1 <= len(text) <= 600
                or text not in context.event_description):
            raise ValueError('Notice quote is not grounded in the supplied text.')
        if not isinstance(stamp, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', stamp):
            raise ValueError('Notice date must be a calendar ISO date.')
        parsed = date.fromisoformat(stamp)
        if parsed not in quoted_dates(text, context):
            raise ValueError('Notice date is not corroborated by its quote.')
        identity = (stamp, text)
        if identity in seen:
            raise ValueError('Duplicate dated notice.')
        seen.add(identity)
        checked.append({'date': stamp, 'quote': text,
                        'after_decision_date': parsed > context.as_of_date})
    blocked = any(item['after_decision_date'] for item in checked)
    evidence = {'validation': 'valid', 'as_of_date': context.as_of_date.isoformat(),
                'model_impact': signal.impact, 'dated_notices': checked,
                'python_temporal_block': blocked,
                'extraction_complete_not_verified': True}
    result = {'impact': signal.impact, 'reason': signal.reason}
    if blocked:
        result = {'impact': 'uncertain', 'reason':
                  'Python detected a dated status notice after the decision date; verify information available at that time.'}
    return result, evidence
