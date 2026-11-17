"""Deterministic constraints, not an LLM judge or truth detector."""
import hashlib
import json
import math
import re

MAX_BYTES = 2_000_000
MAX_CASES = 200
MAX_TEXT = 50_000
TYPES = {'max_words', 'min_words', 'exact_bullets', 'max_headings', 'required_terms', 'forbidden_terms', 'json_object', 'no_markdown'}
NUMERIC = {'max_words', 'min_words', 'exact_bullets', 'max_headings'}

class InputError(ValueError):
    pass

def strict_loads(text):
    def reject(v):
        raise InputError('Non-finite numbers are not allowed.')
    def finite(v):
        number = float(v)
        if not math.isfinite(number):
            reject(v)
        return number
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InputError('Duplicate object key: ' + key)
            result[key] = value
        return result
    try:
        return json.loads(text, parse_constant=reject, parse_float=finite, object_pairs_hook=pairs)
    except RecursionError as exc:
        raise InputError('JSON nesting is too deep.') from exc

def parse(text):
    if len(text.encode('utf-8')) > MAX_BYTES:
        raise InputError('Input exceeds 2 MB.')
    text = text.lstrip('\ufeff').strip()
    if not text:
        raise InputError('Provide JSON or JSONL input.')
    try:
        data = strict_loads(text)
    except json.JSONDecodeError:
        data = []
        for n, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                data.append(strict_loads(line))
            except json.JSONDecodeError as exc:
                raise InputError('Invalid JSON on line %d: %s' % (n, exc.msg)) from exc
    if isinstance(data, dict) and 'cases' in data:
        data = data['cases']
    elif isinstance(data, dict):
        data = [data]
    return validate(data)

def validate(cases):
    if not isinstance(cases, list) or not 1 <= len(cases) <= MAX_CASES:
        raise InputError('Provide 1–200 cases in an array or JSONL file.')
    clean, ids = [], set()
    for index, case in enumerate(cases, 1):
        prefix = 'Case %d: ' % index
        if not isinstance(case, dict):
            raise InputError(prefix + 'must be an object.')
        if set(case) - {'id', 'prompt', 'answer_a', 'answer_b', 'constraints'}:
            raise InputError(prefix + 'unknown fields; use id, prompt, answer_a, answer_b, constraints.')
        item = {}
        for field in ('id', 'prompt', 'answer_a', 'answer_b'):
            value = case.get(field)
            if not isinstance(value, str) or (field in ('id', 'prompt') and not value.strip()):
                raise InputError(prefix + field + ' must be a string (id/prompt cannot be empty).')
            if len(value) > (200 if field == 'id' else MAX_TEXT):
                raise InputError(prefix + field + ' is too long.')
            item[field] = value
        if item['id'] in ids:
            raise InputError(prefix + 'duplicate id: ' + item['id'])
        ids.add(item['id'])
        constraints = case.get('constraints', [])
        if not isinstance(constraints, list) or len(constraints) > 30:
            raise InputError(prefix + 'constraints must be an array of at most 30 checks.')
        checked = []
        for c in constraints:
            if not isinstance(c, dict) or set(c) - {'type', 'value'} or not isinstance(c.get('type'), str) or c.get('type') not in TYPES:
                raise InputError(prefix + 'unknown or malformed constraint.')
            kind, value = c['type'], c.get('value')
            if kind in NUMERIC:
                if type(value) is not int or not 0 <= value <= MAX_TEXT:
                    raise InputError(prefix + kind + ' requires an integer from 0 to 50000.')
            elif kind in {'required_terms', 'forbidden_terms'}:
                if not isinstance(value, list) or not 1 <= len(value) <= 50 or any(not isinstance(v, str) or not v.strip() or len(v) > 200 for v in value):
                    raise InputError(prefix + kind + ' requires 1–50 nonempty strings.')
            elif value is not None:
                raise InputError(prefix + kind + ' does not take a value.')
            checked.append({'type': kind, 'value': value})
        item['constraints'] = checked
        clean.append(item)
    return clean

def metrics(text):
    return {'words': len(re.findall(r"\b\w+(?:['’\-]\w+)*\b", text, re.UNICODE)),
            'headings': len(re.findall(r'^\s{0,3}#{1,6}\s+\S', text, re.M)),
            'paragraphs': len([p for p in re.split(r'\n\s*\n', text.strip()) if p.strip()])}

def _term_present(text, term):
    # Whole-word edges where applicable; punctuation within a phrase stays literal.
    left = r'(?<!\w)' if term[0].isalnum() or term[0] == '_' else ''
    right = r'(?!\w)' if term[-1].isalnum() or term[-1] == '_' else ''
    return re.search(left + re.escape(term) + right, text, re.I) is not None

def check(text, constraint):
    kind, value = constraint['type'], constraint['value']
    m = metrics(text)
    if kind in {'max_words', 'min_words'}:
        count = m['words']
        ok = count <= value if kind == 'max_words' else count >= value
        reason = '%d counted words; %s %d.' % (count, 'maximum' if kind == 'max_words' else 'minimum', value)
    elif kind == 'max_headings':
        count = m['headings']; ok = count <= value
        reason = '%d Markdown ATX headings; maximum %d.' % (count, value)
    elif kind == 'exact_bullets':
        count = len(re.findall(r'^\s*[-+*]\s+\S', text, re.M)); ok = count == value
        reason = '%d unordered bullet lines; expected %d (nested lines also count).' % (count, value)
    elif kind in {'required_terms', 'forbidden_terms'}:
        found = [term for term in value if _term_present(text, term)]
        missing = [term for term in value if term not in found]
        ok = not missing if kind == 'required_terms' else not found
        reason = ('Missing terms: ' + ', '.join(missing)) if kind == 'required_terms' and missing else ('Forbidden terms found: ' + ', '.join(found)) if kind == 'forbidden_terms' and found else 'Literal case-insensitive term check passed.'
    elif kind == 'json_object':
        try:
            result = strict_loads(text)
            ok = isinstance(result, dict)
            reason = 'Valid JSON object.' if ok else 'Valid JSON, but top-level value is not an object.'
        except (ValueError, RecursionError):
            ok = False; reason = 'Not a strict JSON object (fences, duplicate keys and non-finite numbers are rejected).'
    else:
        cues = bool(re.search(r'(^\s{0,3}#{1,6}\s|^\s*[-+*]\s|^\s*\d+[.)]\s|```|\*\*|__|\[[^\]]+\]\([^)]+\))', text, re.M))
        return {'type': kind, 'status': 'fail' if cues else 'review', 'reason': 'Markdown-like formatting found; inspect for literal punctuation.' if cues else 'No common Markdown cues found; this heuristic cannot prove plain-text compliance.'}
    return {'type': kind, 'status': 'pass' if ok else 'fail', 'reason': reason}

def analyze(cases):
    cases = validate(cases)
    canonical = json.dumps(cases, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    if len(canonical.encode('utf-8')) > MAX_BYTES:
        raise InputError('Input exceeds 2 MB.')
    output, total, failures = [], 0, 0
    for case in cases:
        checks = {s: [check(case['answer_' + s], c) for c in case['constraints']] for s in ('a', 'b')}
        counts = {s: sum(c['status'] == 'fail' for c in checks[s]) for s in ('a', 'b')}
        uncertain = any(c['status'] == 'review' for s in checks for c in checks[s])
        empty = not case['answer_a'].strip() or not case['answer_b'].strip()
        if not case['constraints'] or uncertain or empty:
            suggestion, reason = 'review', 'Human review required: missing checks, unresolved heuristic, or empty response.'
        elif counts['a'] == counts['b']:
            suggestion, reason = 'tie', 'Equal explicit-check failure counts; not a quality tie or accuracy judgment.'
        else:
            suggestion = 'A' if counts['a'] < counts['b'] else 'B'
            reason = '%s has fewer explicit-check failures (%d vs %d). This is not an overall quality winner.' % (suggestion, counts['a'], counts['b'])
        total += sum(len(v) for v in checks.values()); failures += sum(counts.values())
        output.append(dict(case, checks=checks, metrics={s: metrics(case['answer_' + s]) for s in ('a', 'b')}, suggestion=suggestion, suggestion_reason=reason))
    return {'batch_id': hashlib.sha256(canonical.encode()).hexdigest(), 'cases': output,
            'summary': {'cases': len(cases), 'checks': total, 'failures': failures},
            'engine': 'comparekit-rules-v1', 'notice': 'Rule checks do not assess truth, safety, nuance, or overall answer quality.'}
