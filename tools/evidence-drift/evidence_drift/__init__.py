"""Evidence Drift Lab: deterministic snapshot diffs, not truth judgments."""
import hashlib
import json

MAX_BYTES = 2_000_000

class SnapshotError(ValueError):
    pass

def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise SnapshotError('Duplicate JSON key: ' + key)
        result[key] = value
    return result

def _string(value, label, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()) or len(value) > 100_000:
        raise SnapshotError(label + ' must be a string of at most 100000 characters.')
    try:
        value.encode('utf-8')
    except UnicodeError as exc:
        raise SnapshotError(label + ' contains invalid Unicode.') from exc
    return value

def _fields(obj, required, label):
    if not isinstance(obj, dict) or set(obj) != set(required):
        raise SnapshotError(label + ' requires exactly: ' + ', '.join(required))

def validate(snapshot):
    _fields(snapshot, ['schema_version', 'snapshot_id', 'captured_at', 'sources', 'answers'], 'Snapshot')
    if type(snapshot['schema_version']) is not int or snapshot['schema_version'] != 1:
        raise SnapshotError('Only schema_version 1 is supported.')
    _string(snapshot['snapshot_id'], 'snapshot_id')
    from datetime import datetime
    try:
        timestamp = datetime.fromisoformat(_string(snapshot['captured_at'], 'captured_at').replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            raise ValueError('Timezone required')
    except ValueError as exc:
        raise SnapshotError('captured_at must be an ISO 8601 timestamp with timezone.') from exc
    for field in ['sources', 'answers']:
        if not isinstance(snapshot[field], list) or len(snapshot[field]) > 1000:
            raise SnapshotError(field + ' must be a list with at most 1000 records.')
    source_ids = set()
    for source in snapshot['sources']:
        _fields(source, ['id', 'url', 'title', 'content'], 'Source')
        for field in source:
            _string(source[field], 'source.' + field, empty=field == 'content')
        from urllib.parse import urlsplit
        try:
            url = urlsplit(source['url'])
            if url.scheme not in ('https', 'http') or not url.hostname or url.username or url.password:
                raise ValueError()
        except ValueError as exc:
            raise SnapshotError('Source URL must be HTTP(S) without credentials.') from exc
        if source['id'] in source_ids:
            raise SnapshotError('Duplicate source id: ' + source['id'])
        source_ids.add(source['id'])
    answer_ids = set()
    for answer in snapshot['answers']:
        _fields(answer, ['id', 'text', 'source_ids'], 'Answer')
        _string(answer['id'], 'answer.id')
        _string(answer['text'], 'answer.text', empty=True)
        refs = answer['source_ids']
        if not isinstance(refs, list) or len(refs) > 1000 or any(not isinstance(x, str) for x in refs):
            raise SnapshotError('answer.source_ids must be a list of strings.')
        if len(set(refs)) != len(refs) or not set(refs) <= source_ids:
            raise SnapshotError('Answer references must be unique and resolve within the snapshot.')
        if answer['id'] in answer_ids:
            raise SnapshotError('Duplicate answer id: ' + answer['id'])
        answer_ids.add(answer['id'])
    return snapshot

def load(path):
    with open(path, 'rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise SnapshotError('Snapshot exceeds 2 MB.')
    try:
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise SnapshotError('Invalid snapshot JSON: ' + str(exc)) from exc
    stack = [(data, 0)]
    while stack:
        value, depth = stack.pop()
        if depth > 100:
            raise SnapshotError('JSON nesting exceeds 100 levels.')
        if isinstance(value, dict):
            stack.extend((v, depth + 1) for v in value.values())
        elif isinstance(value, list):
            stack.extend((v, depth + 1) for v in value)
    return validate(data)

def content_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def snapshot_hash(snapshot):
    # Record and reference order do not affect identity; literal text does.
    normalized = dict(snapshot)
    normalized['sources'] = sorted(snapshot['sources'], key=lambda x: x['id'])
    normalized['answers'] = [dict(a, source_ids=sorted(a['source_ids'])) for a in sorted(snapshot['answers'], key=lambda x: x['id'])]
    return content_hash(json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(',', ':')))

def compare(before, after):
    validate(before); validate(after)
    old = {s['id']: s for s in before['sources']}
    new = {s['id']: s for s in after['sources']}
    changes = []
    for sid in sorted(old.keys() | new.keys()):
        left, right = old.get(sid), new.get(sid)
        if left == right:
            continue
        kind = 'added' if left is None else 'removed' if right is None else 'changed'
        fields = sorted(k for k in ('content', 'url', 'title') if left is None or right is None or left[k] != right[k])
        changes.append({'id': sid, 'kind': kind, 'changed_fields': fields,
                        'before_content_sha256': content_hash(left['content']) if left else None,
                        'after_content_sha256': content_hash(right['content']) if right else None})
    old_answers = {a['id']: a for a in before['answers']}
    new_answers = {a['id']: a for a in after['answers']}
    changed_ids = {c['id'] for c in changes}
    answer_changes = []
    for aid in sorted(old_answers.keys() | new_answers.keys()):
        left, right = old_answers.get(aid), new_answers.get(aid)
        refs = set((left or {}).get('source_ids', [])) | set((right or {}).get('source_ids', []))
        touched = sorted(refs & changed_ids)
        fields = [k for k in ('text', 'source_ids') if left is None or right is None or (set(left[k]) != set(right[k]) if k == 'source_ids' else left[k] != right[k])]
        if fields or touched:
            answer_changes.append({'id': aid, 'kind': 'added' if left is None else 'removed' if right is None else 'changed' if fields else 'unchanged',
                                   'changed_fields': fields, 'changed_source_ids': touched,
                                   'review_required': bool(touched)})
    return {'schema_version': 1, 'before': {'id': before['snapshot_id'], 'sha256': snapshot_hash(before)},
            'after': {'id': after['snapshot_id'], 'sha256': snapshot_hash(after)},
            'source_changes': changes, 'answer_changes': answer_changes,
            'notice': 'Source changes are literal differences. Review flags are dependency signals, not proof of contradiction, factual error, or completeness.'}
