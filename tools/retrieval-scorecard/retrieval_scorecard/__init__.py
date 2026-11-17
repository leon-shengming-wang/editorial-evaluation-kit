"""Deterministic offline evaluation of explicit relevance judgments."""
import hashlib
import html
import json
import math

MAX_BYTES = 2_000_000

class InputError(ValueError):
    pass

def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise InputError('Duplicate JSON key: ' + key)
        result[key] = value
    return result

def _reject(value):
    raise InputError('Non-finite numbers are not allowed.')

def load(path):
    with open(path, 'rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise InputError('Input exceeds 2 MB.')
    try:
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_reject)
        stack = [(data, 0)]
        while stack:
            value, depth = stack.pop()
            if depth > 100:
                raise InputError('Nesting exceeds 100 levels.')
            if isinstance(value, float) and not math.isfinite(value):
                _reject(value)
            if isinstance(value, dict):
                stack.extend((v, depth + 1) for v in value.values())
            elif isinstance(value, list):
                stack.extend((v, depth + 1) for v in value)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise InputError('Invalid JSON: ' + str(exc)) from exc
    return data

def fields(obj, expected):
    if not isinstance(obj, dict) or set(obj) != set(expected):
        raise InputError('Expected exactly these fields: ' + ', '.join(expected))

def identifier(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise InputError('IDs must be nonempty strings of at most 200 characters.')
    try:
        value.encode('utf-8')
    except UnicodeError as exc:
        raise InputError('Invalid Unicode in ID.') from exc

def validate(qrels, run):
    fields(qrels, ['schema_version', 'queries'])
    fields(run, ['schema_version', 'run_id', 'queries'])
    for data in (qrels, run):
        if type(data['schema_version']) is not int or data['schema_version'] != 1:
            raise InputError('schema_version must be integer 1.')
        if not isinstance(data['queries'], list) or len(data['queries']) > 1000:
            raise InputError('queries must be a list of at most 1000 queries.')
    if not qrels['queries']:
        raise InputError('At least one qrels query is required.')
    identifier(run['run_id'])
    judgments, rankings = {}, {}
    total = 0
    for data, target, field in ((qrels, judgments, 'judgments'), (run, rankings, 'documents')):
        for query in data['queries']:
            fields(query, ['id', field]); identifier(query['id'])
            if query['id'] in target:
                raise InputError('Duplicate query ID: ' + query['id'])
            records = query[field]
            if not isinstance(records, list) or len(records) > 10000:
                raise InputError(field + ' must be an array of at most 10000 records.')
            total += len(records)
            if total > 100000:
                raise InputError('Too many records (maximum 100000 combined).')
            seen = set(); values = {} if field == 'judgments' else []
            for record in records:
                if field == 'judgments':
                    fields(record, ['document_id', 'relevance'])
                    doc, grade = record['document_id'], record['relevance']
                    if type(grade) not in (int, float) or not 0 <= grade <= 1000 or not math.isfinite(grade):
                        raise InputError('Relevance must be a finite number from 0 to 1000 (not boolean).')
                else:
                    doc = record
                identifier(doc)
                if doc in seen:
                    raise InputError('Duplicate document ID within query: ' + doc)
                seen.add(doc)
                if field == 'judgments': values[doc] = grade
                else: values.append(doc)
            target[query['id']] = values
    return judgments, rankings

def _hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def evaluate(qrels, run, k=10):
    if type(k) is not int or not 1 <= k <= 10000:
        raise InputError('k must be an integer from 1 to 10000.')
    judgments, rankings = validate(qrels, run)
    rows = []
    for qid in sorted(judgments):
        labels = judgments[qid]
        docs = rankings.get(qid, [])[:k]
        relevant = sum(v > 0 for v in labels.values())
        evidence = []
        for rank, doc in enumerate(docs, 1):
            gain = labels.get(doc, 0)
            evidence.append({'rank': rank, 'document_id': doc, 'judged': doc in labels,
                             'relevance': labels.get(doc), 'gain': gain,
                             'relevant': gain > 0, 'dcg_contribution': gain / math.log2(rank + 1)})
        hits = sum(e['relevant'] for e in evidence)
        dcg = math.fsum(e['dcg_contribution'] for e in evidence)
        ideal = sorted(labels.items(), key=lambda pair: (-pair[1], pair[0]))[:k]
        ideal_evidence = [{'rank': rank, 'document_id': doc, 'gain': gain, 'dcg_contribution': gain / math.log2(rank + 1)} for rank, (doc, gain) in enumerate(ideal, 1)]
        idcg = math.fsum(e['dcg_contribution'] for e in ideal_evidence)
        # Normalize gains before taking the ratio, avoiding subnormal DCG division.
        max_grade = max(labels.values(), default=0)
        scaled_dcg = math.fsum((e['gain'] / max_grade) / math.log2(e['rank'] + 1) for e in evidence) if max_grade else 0.0
        scaled_ideal = math.fsum((e['gain'] / max_grade) / math.log2(e['rank'] + 1) for e in ideal_evidence) if max_grade else 0.0
        rr = next((1 / e['rank'] for e in evidence if e['relevant']), 0.0)
        rows.append({'query_id': qid, 'missing_run_query': qid not in rankings,
                     'judged_documents': len(labels), 'relevant_documents': relevant,
                     'retrieved_total': len(rankings.get(qid, [])), 'retrieved_at_k': len(docs),
                     'unjudged_at_k': sum(not e['judged'] for e in evidence),
                     'relevant_at_k': hits, 'precision_at_k': hits / k,
                     'recall_at_k': hits / relevant if relevant else 0.0,
                     'rr_at_k': rr, 'dcg_at_k': dcg, 'ideal_dcg_at_k': idcg,
                     'ndcg_at_k': scaled_dcg / scaled_ideal if scaled_ideal else 0.0,
                     'ndcg_gain_scale': max_grade, 'scaled_dcg_at_k': scaled_dcg, 'scaled_ideal_dcg_at_k': scaled_ideal,
                     'ranking_evidence': evidence, 'ideal_ranking_evidence': ideal_evidence})
    summary = {name: math.fsum(r[field] for r in rows) / len(rows) for name, field in [('precision_at_k','precision_at_k'),('recall_at_k','recall_at_k'),('mrr_at_k','rr_at_k'),('ndcg_at_k','ndcg_at_k')]}
    summary.update(query_count=len(rows), missing_run_queries=sum(r['missing_run_query'] for r in rows), zero_relevance_queries=sum(r['relevant_documents'] == 0 for r in rows))
    return {'schema_version': 1, 'engine': 'retrieval-scorecard-v1', 'run_id': run['run_id'], 'k': k,
            'input_sha256': {'qrels': _hash(qrels), 'run': _hash(run)},
            'policy': {'gain': 'linear relevance / log2(rank + 1)', 'binary_relevance': 'grade > 0', 'unjudged': 'gain zero; retained in ranking', 'query_universe': 'all qrels queries; extra run queries excluded', 'zero_relevance': 'recall and nDCG set to zero; included in macro mean', 'precision_denominator': 'k even for short runs'},
            'excluded_run_queries': sorted(set(rankings) - set(judgments)), 'summary': summary, 'queries': rows,
            'notice': 'Offline scores depend on supplied judgments. They do not establish factual truth, answer quality, retrieval coverage, or real-world benchmark performance.'}

def render_html(report):
    esc = lambda value: html.escape(str(value), quote=True)
    score = lambda value: format(value, '.4f')
    summary = report['summary']
    parts = ["""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Retrieval Scorecard</title><style>
    *{box-sizing:border-box}body{font:15px/1.6 system-ui,sans-serif;margin:0;color:#18383f;background:#f1f5f4}main{max-width:1160px;margin:auto;padding:48px 24px 72px}.eyebrow{font-size:12px;font-weight:750;letter-spacing:.15em;text-transform:uppercase;color:#287563}h1{font-size:clamp(32px,5vw,48px);letter-spacing:-.045em;line-height:1.15;margin:12px 0}h2{font-size:21px;letter-spacing:-.02em;margin:0 0 16px}p{max-width:85ch}.muted,small{color:#547077}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:28px 0}.card,section{background:#fff;border:1px solid #d9e4e1;border-radius:14px}.card{padding:20px}.card strong{display:block;font-size:34px;font-variant-numeric:tabular-nums;line-height:1.3;letter-spacing:-.04em}.card span{font-size:13px;color:#547077}section{padding:24px;margin:20px 0}.strip{display:flex;flex-wrap:wrap;gap:12px 24px;font-size:13px;margin:20px 0}.strip b{color:#18383f}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th{text-align:left;color:#547077;font-size:11px;letter-spacing:.05em;text-transform:uppercase}td,th{padding:12px 10px;border-bottom:1px solid #e5edeb}td{font-variant-numeric:tabular-nums}td:first-child{font-weight:650;min-width:140px;overflow-wrap:anywhere}tr:last-child td{border-bottom:0}.badge{display:inline-block;border-radius:20px;padding:3px 9px;background:#e6f2ec;color:#27604c;font-size:11px;white-space:nowrap}.warn{background:#fff1d8;color:#8a5919}details{border-top:1px solid #e3ece9;padding-top:16px;margin-top:16px}summary{cursor:pointer;font-weight:650}details p{font-size:13px}.policy{display:grid;grid-template-columns:1fr 1fr;gap:16px 32px}.policy strong{display:block;font-size:13px}.policy span{font-size:13px;color:#547077}.hash{overflow-wrap:anywhere;font:11px/1.7 ui-monospace,monospace}.notice{border-left:3px solid #c99a49;padding-left:16px;font-size:13px}.query-heading{display:flex;justify-content:space-between;gap:16px;align-items:center}.query-heading h2{overflow-wrap:anywhere;margin:0}.metrics-inline{display:flex;flex-wrap:wrap;gap:10px 25px;margin-top:18px;font-size:13px}.metrics-inline b{font-variant-numeric:tabular-nums}@media(max-width:700px){main{padding:28px 16px}.cards{grid-template-columns:repeat(2,1fr)}section{padding:18px}.policy{grid-template-columns:1fr}.card strong{font-size:28px}.query-heading{align-items:flex-start;flex-direction:column}}
    </style></head><body><main><div class="eyebrow">Offline evaluation / inspectable evidence</div><h1>Retrieval Scorecard</h1>"""]
    parts.append('<p class="muted">'+esc(report['run_id'])+' · Top '+esc(report['k'])+' results · Linear graded gain</p>')
    parts.append('<div class="cards">')
    for field, label, description in [('precision_at_k','Precision','Relevant hits / cutoff'),('recall_at_k','Recall','Relevant hits / judged relevant'),('mrr_at_k','MRR','First relevant result'),('ndcg_at_k','nDCG','Graded ranking quality')]:
        parts.append('<div class="card"><span>'+label+' @ '+esc(report['k'])+'</span><strong>'+score(summary[field])+'</strong><span>'+description+'</span></div>')
    parts.append('</div><div class="strip"><span><b>'+esc(summary['query_count'])+'</b> evaluated queries</span><span><b>'+esc(summary['missing_run_queries'])+'</b> missing run queries</span><span><b>'+esc(summary['zero_relevance_queries'])+'</b> zero-relevance queries</span><span><b>'+esc(len(report['excluded_run_queries']))+'</b> excluded run queries</span></div>')
    parts.append('<p class="notice">'+esc(report['notice'])+' Values above are equally weighted query averages, not benchmark claims.</p>')
    parts.append('<section><h2>Query overview</h2><div class="scroll"><table><tr><th>Query</th><th>P @ k</th><th>R @ k</th><th>RR @ k</th><th>nDCG @ k</th><th>Missing run</th><th>Unjudged @ k</th></tr>')
    for q in report['queries']:
        values = [q['query_id']] + [score(q[f]) for f in ('precision_at_k','recall_at_k','rr_at_k','ndcg_at_k')] + ['Yes' if q['missing_run_query'] else 'No', q['unjudged_at_k']]
        parts.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in values)+'</tr>')
    parts.append('</table></div><small>RR is per-query reciprocal rank; its macro mean is MRR. Unjudged results are not verified irrelevant.</small></section>')
    policies = [('Query universe','All qrels queries count equally. Missing runs score zero; extra run queries are excluded.'),('Unjudged documents','Retained at their original rank with zero gain. Unknown labels stay distinguishable from explicit zero judgments.'),('Binary relevance and precision','Any grade above zero is relevant. Precision always divides by k, even for a short run.'),('Graded ranking','DCG uses grade / log2(rank + 1). Ideal DCG uses all judgments in descending grade order.'),('Zero-relevance convention','Recall and nDCG are set to zero when their denominator is zero. These queries remain in the macro mean.'),('Display precision','Scores are rounded to four decimals here. JSON retains numeric precision. nDCG uses max-grade-scaled gains to avoid tiny-number underflow; raw DCG can underflow.')]
    parts.append('<section><h2>How to read these scores</h2><div class="policy">')
    for title, description in policies:
        parts.append('<div><strong>'+title+'</strong><span>'+description+'</span></div>')
    parts.append('</div><p><small>Excluded run queries: '+esc(', '.join(report['excluded_run_queries']) or 'None')+'</small></p></section><h2>Per-query evidence</h2>')
    for q in report['queries']:
        badge = '<span class="badge warn">Missing run</span>' if q['missing_run_query'] else '<span class="badge">Run supplied</span>'
        parts.append('<section><div class="query-heading"><h2>'+esc(q['query_id'])+'</h2>'+badge+'</div><div class="metrics-inline">')
        for label, value in [('Relevant hits',q['relevant_at_k']),('Judged relevant',q['relevant_documents']),('Retrieved / total',str(q['retrieved_at_k'])+' / '+str(q['retrieved_total'])),('DCG',score(q['dcg_at_k'])),('Ideal DCG',score(q['ideal_dcg_at_k']))]:
            parts.append('<span>'+label+': <b>'+esc(value)+'</b></span>')
        parts.append('</div>')
        for key, title in [('ranking_evidence','Retrieved ranking'),('ideal_ranking_evidence','Ideal ranking from judgments')]:
            parts.append('<details><summary>'+title+' ('+esc(len(q[key]))+')</summary>')
            if not q[key]:
                parts.append('<p class="muted">No documents in this ranking.</p>')
            else:
                parts.append('<div class="scroll"><table><tr><th>Rank</th><th>Document</th><th>Judgment</th><th>Gain</th><th>DCG contribution</th></tr>')
                for e in q[key]:
                    label = 'Unjudged' if e.get('judged') is False else e.get('relevance',e['gain'])
                    parts.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in [e['rank'],e['document_id'],label,e['gain'],score(e['dcg_contribution'])])+'</tr>')
                parts.append('</table></div>')
            parts.append('</details>')
        parts.append('</section>')
    parts.append('<section><details><summary>Reproducibility / input fingerprints</summary><p class="muted">SHA-256 identifies supplied input data, not source authenticity.</p>')
    for label, value in report['input_sha256'].items():
        parts.append('<p><strong>'+esc(label)+'</strong><br><span class="hash">'+esc(value)+'</span></p>')
    parts.append('</details></section></main></body></html>')
    return ''.join(parts)
