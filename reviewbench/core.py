"""Strict validation and deterministic summaries; no model or network calls."""
import json
import re
from collections import Counter
from pathlib import Path

DIMENSIONS = ('accuracy', 'instructions', 'clarity')
CATEGORIES = ('editorial', 'fact-check', 'design', 'audio', 'language')
FIELDS = {'id', 'category', 'prompt', 'source', 'responses', 'scores', 'winner',
          'rationale', 'evidence', 'uncertainty', 'synthetic'}

class DatasetError(ValueError):
    """Readable validation errors, including source line numbers."""

def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DatasetError('duplicate JSON key: ' + key)
        result[key] = value
    return result

def reject_constant(value):
    raise DatasetError('non-finite JSON number: ' + value)

def total(scores):
    return scores['accuracy'] * 2 + scores['instructions'] + scores['clarity']

def validate(record):
    """Return all recoverable errors for one record, without mutating input."""
    errors = []
    if not isinstance(record, dict):
        return ['record must be an object']
    missing, extra = FIELDS - record.keys(), record.keys() - FIELDS
    if missing: errors.append('missing fields: ' + ', '.join(sorted(missing)))
    if extra: errors.append('unknown fields: ' + ', '.join(sorted(extra)))
    for key in ('id', 'category', 'prompt', 'source', 'rationale', 'uncertainty'):
        value = record.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(key + ' must be nonempty text')
    if isinstance(record.get('id'), str) and not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,63}', record['id']):
        errors.append('id must be 3-64 lowercase letters, digits or hyphens')
    if record.get('category') not in CATEGORIES: errors.append('invalid category')
    if record.get('synthetic') is not True: errors.append('synthetic must be true')
    if record.get('winner') not in ('A', 'B', 'tie', 'abstain'): errors.append('invalid winner')
    responses = record.get('responses')
    responses_ok = isinstance(responses, dict) and set(responses) == {'A', 'B'}
    if not responses_ok:
        errors.append('responses must contain exactly A and B')
    else:
        for side in ('A', 'B'):
            if not isinstance(responses[side], str) or not responses[side].strip():
                errors.append('response ' + side + ' must be nonempty text')
                responses_ok = False
    scores = record.get('scores')
    scores_ok = isinstance(scores, dict) and set(scores) == {'A', 'B'}
    if not scores_ok: errors.append('scores must contain exactly A and B')
    else:
        for side in ('A', 'B'):
            values = scores[side]
            if not isinstance(values, dict) or set(values) != set(DIMENSIONS):
                errors.append('scores ' + side + ' must contain exactly the three dimensions')
                scores_ok = False
                continue
            for dimension in DIMENSIONS:
                if type(values[dimension]) is not int or not 1 <= values[dimension] <= 5:
                    errors.append(side + '.' + dimension + ' must be an integer from 1 to 5')
                    scores_ok = False
    if scores_ok and record.get('winner') in ('A', 'B', 'tie'):
        a, b = total(scores['A']), total(scores['B'])
        expected = 'A' if a > b else 'B' if b > a else 'tie'
        if record['winner'] != expected:
            errors.append('winner contradicts weighted scores; expected ' + expected)
    evidence = record.get('evidence')
    if not isinstance(evidence, list) or not evidence:
        errors.append('evidence must be a nonempty list')
    else:
        for index, item in enumerate(evidence):
            label = 'evidence[' + str(index) + ']'
            if not isinstance(item, dict) or set(item) != {'response', 'quote', 'reason'}:
                errors.append(label + ' must contain response, quote and reason')
                continue
            if item['response'] not in ('A', 'B'):
                errors.append(label + ' has invalid response')
            for key in ('quote', 'reason'):
                if not isinstance(item[key], str) or not item[key].strip():
                    errors.append(label + '.' + key + ' must be nonempty text')
            if responses_ok and item['response'] in ('A', 'B') and isinstance(item['quote'], str):
                if item['quote'] not in responses[item['response']]:
                    errors.append(label + ' quote is not an exact response substring')
    return errors

def load(path):
    records, errors, seen = [], [], set()
    with Path(path).open(encoding='utf-8') as source:
        for number, line in enumerate(source, 1):
            if not line.strip(): continue
            try:
                record = json.loads(line, object_pairs_hook=strict_object, parse_constant=reject_constant)
            except (ValueError, RecursionError) as exc:
                errors.append('line {}: {}'.format(number, exc))
                continue
            problems = validate(record)
            if isinstance(record, dict) and isinstance(record.get('id'), str):
                if record['id'] in seen: problems.append('duplicate record id: ' + record['id'])
                seen.add(record['id'])
            errors.extend('line {}: {}'.format(number, message) for message in problems)
            records.append(record)
    if not records and not errors: errors.append('dataset contains no records')
    if errors: raise DatasetError('\n'.join(errors))
    return records

def summarize(records):
    return {'records': len(records), 'categories': dict(sorted(Counter(r['category'] for r in records).items())),
            'decisions': {key: sum(r['winner'] == key for r in records) for key in ('A', 'B', 'tie', 'abstain')},
            'scope': 'Synthetic demonstration, not model performance or human agreement measurement.'}
