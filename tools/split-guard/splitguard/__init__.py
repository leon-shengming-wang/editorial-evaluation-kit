"""Auditable cross-split text similarity, not a model-contamination detector."""
import hashlib
import html
import json
import math
import re
import unicodedata
from collections import defaultdict

MAX_BYTES = 2_000_000
MAX_RECORDS = 400
MAX_TOKENS = 4000
MAX_SHINGLES = 100000
MAX_VISITS = 1000000

class InputError(ValueError):
    pass

def _pairs(items):
    result = {}
    for k, v in items:
        if k in result:
            raise InputError('Duplicate JSON key: ' + k)
        result[k] = v
    return result

def load(path):
    with open(path, 'rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise InputError('Input exceeds 2 MB.')
    try:
        text = raw.decode('utf-8-sig')
        records = []
        for n, line in enumerate(text.splitlines(), 1):
            if line.strip():
                try:
                    records.append(json.loads(line, object_pairs_hook=_pairs))
                except (ValueError, RecursionError) as exc:
                    raise InputError('Invalid JSONL line %d: %s' % (n, exc)) from exc
    except UnicodeError as exc:
        raise InputError('Input must be UTF-8.') from exc
    return validate(records)

def validate(records):
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_RECORDS:
        raise InputError('Provide 1–400 records.')
    ids = set()
    for record in records:
        if not isinstance(record, dict) or set(record) - {'id','split','text','label'} or not {'id','split','text'} <= set(record):
            raise InputError('Each record requires id, split, text; optional label only.')
        for field in record:
            value = record[field]
            if not isinstance(value, str) or not value.strip() or len(value) > (50000 if field == 'text' else 200):
                raise InputError(field + ' must be a nonempty bounded string.')
            try:
                value.encode('utf-8')
            except UnicodeError as exc:
                raise InputError('Invalid Unicode in ' + field) from exc
        if record['split'] not in {'train','dev','test'}:
            raise InputError('split must be train, dev or test.')
        if record['id'] in ids:
            raise InputError('Duplicate record id: ' + record['id'])
        ids.add(record['id'])
    if len(json.dumps(records, ensure_ascii=False).encode()) > MAX_BYTES:
        raise InputError('Validated input exceeds 2 MB.')
    return records

def normalized(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())

def tokens(text):
    return re.findall(r'\w+', normalized(text), re.UNICODE)

def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def audit(records, threshold=0.7, shingle_size=3):
    validate(records)
    if isinstance(threshold, bool) or not isinstance(threshold, (int,float)) or not 0 < threshold <= 1 or not math.isfinite(threshold):
        raise InputError('threshold must be finite and in (0, 1].')
    if type(shingle_size) is not int or not 1 <= shingle_size <= 10:
        raise InputError('shingle_size must be an integer from 1 to 10.')
    rows = sorted(records, key=lambda r:r['id'])
    normals, shingles, groups = [], [], defaultdict(list)
    for i, row in enumerate(rows):
        normal = normalized(row['text']); words = tokens(row['text'])
        if len(words) > MAX_TOKENS:
            raise InputError('Record exceeds 4000 tokens: ' + row['id'])
        normals.append(normal); groups[normal].append(i)
        shingles.append(set(tuple(words[k:k+shingle_size]) for k in range(len(words)-shingle_size+1)))
    if sum(map(len, shingles)) > MAX_SHINGLES:
        raise InputError('Batch exceeds 100000 distinct document-shingle entries.')
    exact = set()
    for group in groups.values():
        for p, a in enumerate(group):
            for b in group[p+1:]:
                if rows[a]['split'] != rows[b]['split']:
                    exact.add((a,b))
    index = defaultdict(list); candidates = set(); visits = 0
    for i, grams in enumerate(shingles):
        for gram in sorted(grams):
            for j in index[gram]:
                visits += 1
                if visits > MAX_VISITS:
                    raise InputError('Comparison budget exceeded (1000000 posting visits). Split into smaller documented batches; no partial report produced.')
                if rows[i]['split'] != rows[j]['split'] and (j,i) not in exact:
                    candidates.add((j,i))
            index[gram].append(i)
    findings = []
    for a,b in sorted(exact | candidates):
        left,right = rows[a],rows[b]; common=shingles[a]&shingles[b]; union=shingles[a]|shingles[b]
        score=len(common)/len(union) if union else None
        is_exact=(a,b) in exact
        if not is_exact and (score is None or score < threshold):
            continue
        findings.append({'left_id':left['id'],'right_id':right['id'],'left_split':left['split'],'right_split':right['split'],
            'kind':'normalized_exact' if is_exact else 'near_candidate','jaccard':score,
            'shared_shingles':len(common),'union_shingles':len(union),'shared_examples':[' '.join(g) for g in sorted(common)[:5]],
            'left_sha256':digest(left['text']),'right_sha256':digest(right['text']),
            'left_excerpt':left['text'][:240],'right_excerpt':right['text'][:240],
            'label_conflict':left['label']!=right['label'] if 'label' in left and 'label' in right else None,
            'left_label':left.get('label'),'right_label':right.get('label')})
    possible=sum(rows[a]['split']!=rows[b]['split'] for a in range(len(rows)) for b in range(a+1,len(rows)))
    return {'engine':'splitguard-v1','input_sha256':digest(json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':'))),
        'settings':{'threshold':threshold,'shingle_size':shingle_size,'normalization':'NFKC, casefold, collapsed whitespace; punctuation retained for exact'},
        'coverage':{'records':len(rows),'cross_split_pairs':possible,'exact_pairs':len(exact),'near_candidate_pairs_scored':len(candidates),
                    'posting_visits':visits,'near_ineligible_ids':[rows[i]['id'] for i,g in enumerate(shingles) if not g],
                    'complete_within_declared_rules':True},
        'findings':findings,'notice':'Similarity candidates require human review. No records are deleted. This is not proof that a model trained on a benchmark.'}

def render(report):
    e=lambda x:html.escape(str(x))
    items=[]
    for f in report['findings']:
        items.append('<article><h2>%s ↔ %s</h2><p>%s → %s · %s · Jaccard %s</p><div class="pair"><pre>%s</pre><pre>%s</pre></div><p>Shared / union shingles: %s / %s. Label conflict: %s.</p><p>Shared examples: %s</p><details><summary>Content fingerprints</summary><code>%s<br>%s</code></details></article>' % tuple(e(x) for x in [f['left_id'],f['right_id'],f['left_split'],f['right_split'],f['kind'],'N/A (short exact text)' if f['jaccard'] is None else round(f['jaccard'],4),f['left_excerpt'],f['right_excerpt'],f['shared_shingles'],f['union_shingles'],('Not comparable' if f['label_conflict'] is None else 'Yes' if f['label_conflict'] else 'No'),' | '.join(f['shared_examples']),f['left_sha256'],f['right_sha256']]))
    coverage = report['coverage']; settings = report['settings']
    cards = ''.join('<div class="stat"><strong>%s</strong><span>%s</span></div>' % (e(value), e(label)) for value,label in [
        (coverage['records'], 'Records'), (coverage['cross_split_pairs'], 'Cross-split pairs'),
        (coverage['exact_pairs'], 'Exact matches'), (len(report['findings']) - coverage['exact_pairs'], 'Near-match candidates')])
    short_ids = ', '.join(coverage['near_ineligible_ids']) or 'None'
    coverage_text = '%s non-exact pairs scored; %s index posting visits. All pairs covered under the declared rules; no sampling.' % (coverage['near_candidate_pairs_scored'], coverage['posting_visits'])
    rule_text = 'Near-match threshold: %s. Shingle width: %s tokens. Exact normalization: NFKC, casefold and collapsed whitespace; punctuation retained.' % (settings['threshold'], settings['shingle_size'])
    header = '<div class="stats">' + cards + '</div><p>' + e(coverage_text) + '</p><p>' + e(rule_text) + '</p><p>Too short for near scoring (still checked for exact matches): ' + e(short_ids) + '</p>'
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Split Guard audit</title><style>body{font:16px system-ui;background:#f3f5f1;color:#19322c;max-width:1100px;margin:48px auto;padding:20px}h1{font-size:44px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}.stat{background:#e3ebe3;border-radius:12px;padding:18px}.stat strong{display:block;font-size:30px}.stat span{display:block;font-size:13px;color:#456056}article{background:white;border:1px solid #d6ddd6;border-radius:12px;padding:24px;margin:20px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}pre,code{white-space:pre-wrap;overflow-wrap:anywhere}pre{background:#f4f6f4;padding:18px}small{color:#53665d}@media(max-width:650px){.stats{grid-template-columns:1fr 1fr}.pair{grid-template-columns:1fr}h1{font-size:32px}}</style><header><small>DATASET QUALITY · LOCAL EVIDENCE</small><h1>Split Guard</h1><p>'+e(report['notice'])+'</p><p>'+e(report.get('dataset_notice', 'User-supplied dataset; provenance is not verified.'))+'</p>'+header+'<details><summary>Input fingerprint</summary><code>'+e(report['input_sha256'])+'</code></details></header>'+(''.join(items) or '<article>No findings under these rules. This does not establish absence of semantic overlap.</article>')+'</html>'
