"""Paired evaluation regression analysis; imported scores, not model judging."""
import hashlib
import html
import json
import math
import random

MAX_BYTES = 2_000_000
class InputError(ValueError):
    pass

def _text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 500:
        raise InputError(label + ' must be nonempty text of at most 500 characters.')
    try:
        value.encode('utf-8')
    except UnicodeError as exc:
        raise InputError('Invalid Unicode in ' + label) from exc

def validate(run):
    fields = {'schema_version','run_id','dataset_id','dataset_version','metric','direction','items'}
    if not isinstance(run, dict) or set(run) != fields:
        raise InputError('Run requires exactly: ' + ', '.join(sorted(fields)))
    if type(run['schema_version']) is not int or run['schema_version'] != 1:
        raise InputError('schema_version must be 1.')
    for key in ('run_id','dataset_id','dataset_version','metric'):
        _text(run[key], key)
    if run['direction'] not in ('higher','lower'):
        raise InputError('direction must be higher or lower.')
    if not isinstance(run['items'], list) or not 1 <= len(run['items']) <= 1000:
        raise InputError('items must contain 1–1000 records.')
    ids = set()
    for item in run['items']:
        if not isinstance(item, dict) or set(item) != {'id','score','slice'}:
            raise InputError('Each item requires id, score and slice.')
        _text(item['id'], 'item.id'); _text(item['slice'], 'item.slice')
        if item['id'] in ids:
            raise InputError('Duplicate item id: ' + item['id'])
        ids.add(item['id'])
        score = item['score']
        if type(score) not in (int,float) or not 0 <= score <= 1 or not math.isfinite(score):
            raise InputError('Scores must be finite numbers in [0,1].')
    return run

def load(path):
    def pairs(entries):
        d = {}
        for k,v in entries:
            if k in d:
                raise InputError('Duplicate JSON key: ' + k)
            d[k] = v
        return d
    with open(path, 'rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise InputError('Input exceeds 2 MB.')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs)
        stack = [(value, 0)]
        while stack:
            v,depth = stack.pop()
            if depth > 100:
                raise InputError('JSON nesting exceeds 100 levels.')
            if isinstance(v, dict): stack.extend((x,depth+1) for x in v.values())
            elif isinstance(v, list): stack.extend((x,depth+1) for x in v)
        return validate(value)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise InputError('Invalid run: ' + str(exc)) from exc

def quantile(values, q):
    ordered = sorted(values)
    index = (len(ordered)-1)*q
    lo = int(index); hi = min(lo+1,len(ordered)-1)
    return ordered[lo] + (ordered[hi]-ordered[lo])*(index-lo)

def summarize(rows, resamples, seed):
    n = len(rows)
    if not n:
        return {'n':0,'baseline_mean':None,'candidate_mean':None,'mean_improvement':None,'ci95':None,'signal':'unavailable','warnings':['No matched items.']}
    deltas = [r['improvement'] for r in rows]
    mean = math.fsum(deltas)/n
    warnings = []
    if n < 20: warnings.append('Small sample (fewer than 20 pairs); interval may be unstable.')
    if len(set(deltas)) == 1: warnings.append('Constant observed differences; degenerate resampling does not establish certainty.')
    interval = None
    if n >= 2:
        rng = random.Random(seed)
        samples = [math.fsum(deltas[rng.randrange(n)] for _ in range(n))/n for _ in range(resamples)]
        interval = [quantile(samples,.025),quantile(samples,.975)]
    else: warnings.append('One pair: confidence interval suppressed.')
    signal = 'uncertain'
    if n >= 20 and len(set(deltas)) > 1 and interval:
        signal = 'positive_interval' if interval[0] > 0 else 'negative_interval' if interval[1] < 0 else 'uncertain'
    return {'n':n,'baseline_mean':math.fsum(r['baseline'] for r in rows)/n,'candidate_mean':math.fsum(r['candidate'] for r in rows)/n,'mean_improvement':mean,'ci95':interval,'signal':signal,'warnings':warnings}

def fingerprint(run):
    return hashlib.sha256(json.dumps(dict(run,items=sorted(run['items'],key=lambda x:x['id'])),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def compare(baseline, candidate, resamples=2000, seed=17):
    validate(baseline);validate(candidate)
    if type(resamples) is not int or not 100 <= resamples <= 5000: raise InputError('resamples must be 100–5000.')
    if type(seed) is not int or not 0 <= seed <= 2**32-1: raise InputError('seed must be an integer in [0, 2^32-1].')
    for field in ('dataset_id','dataset_version','metric','direction'):
        if baseline[field] != candidate[field]: raise InputError('Incomparable runs: ' + field + ' differs.')
    a = {x['id']:x for x in baseline['items']};b={x['id']:x for x in candidate['items']}
    rows=[]
    sign=1 if baseline['direction']=='higher' else -1
    for key in sorted(a.keys() & b.keys()):
        if a[key]['slice'] != b[key]['slice']: raise InputError('Slice changed for matched item: ' + key)
        raw=b[key]['score']-a[key]['score']
        rows.append({'id':key,'slice':a[key]['slice'],'baseline':a[key]['score'],'candidate':b[key]['score'],'raw_delta':raw,'improvement':sign*raw})
    slices={s:summarize([r for r in rows if r['slice']==s],resamples,seed) for s in sorted({r['slice'] for r in rows})}
    return {'schema_version':1,'baseline':{'run_id':baseline['run_id'],'sha256':fingerprint(baseline)},'candidate':{'run_id':candidate['run_id'],'sha256':fingerprint(candidate)},'dataset_id':baseline['dataset_id'],'dataset_version':baseline['dataset_version'],'metric':baseline['metric'],'direction':baseline['direction'],'method':{'name':'paired percentile bootstrap of mean improvement','resamples':resamples,'seed':seed,'confidence':.95},'coverage':{'baseline_count':len(a),'candidate_count':len(b),'matched':len(rows),'baseline_only':sorted(a.keys()-b.keys()),'candidate_only':sorted(b.keys()-a.keys()),'complete':a.keys()==b.keys()},'overall':summarize(rows,resamples,seed),'slices':slices,'items':rows,'notice':'Imported scores are not independently verified. Paired intervals assume independent representative items; they do not account for evaluator/model randomness, multiple comparisons, or missing-item bias. Positive improvement is better under the declared direction. No production or significance guarantee.'}

def render(report):
    e=lambda x:html.escape(str(x),quote=True)
    def number(x): return 'Unavailable' if x is None else '%.4f'%x
    def stat(label,stat):
        ci=stat['ci95'];ci_text='Unavailable' if ci is None else '[%.4f, %.4f]'%tuple(ci)
        return '<tr><td>'+e(label)+'</td><td>'+str(stat['n'])+'</td><td>'+number(stat['baseline_mean'])+'</td><td>'+number(stat['candidate_mean'])+'</td><td>'+number(stat['mean_improvement'])+'</td><td>'+ci_text+'</td><td>'+e(stat['signal'])+'</td></tr>'
    stats=stat('Overall (matched only)',report['overall'])+''.join(stat(k,v) for k,v in report['slices'].items())
    rows=''.join('<tr>'+''.join('<td>'+(e(r[k]) if k in ('id','slice') else number(r[k]))+'</td>' for k in ('id','slice','baseline','candidate','raw_delta','improvement'))+'</tr>' for r in report['items'])
    warnings=''.join('<li>'+e(w)+'</li>' for w in report['overall']['warnings'])
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evaluation Regression Lab</title><style>body{font:16px system-ui;background:#f4f5f8;color:#182434;max-width:1200px;margin:40px auto;padding:0 24px}h1{font-size:42px}header{border-top:6px solid #3154a3;padding:20px 0}.panel{background:white;border:1px solid #d8dce5;border-radius:12px;padding:22px;margin:20px 0;overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid #ddd;padding:10px;text-align:left}p{line-height:1.6}code{overflow-wrap:anywhere}.tag{color:#3154a3;font-weight:bold}details{margin:16px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><header><div class="tag">PAIRED RESULTS · EXPLICIT UNCERTAINTY</div><h1>Evaluation Regression Lab</h1><p>Compare scored runs without hiding coverage gaps or uncertainty.</p></header>'''+ '<section class="panel"><h2>'+e(report['baseline']['run_id'])+' → '+e(report['candidate']['run_id'])+'</h2><p>Metric: '+e(report['metric'])+' · '+e(report['direction'])+' is better. Dataset: '+e(report['dataset_id'])+' / '+e(report['dataset_version'])+'</p><p>'+e(report['notice'])+'</p><ul>'+warnings+'</ul><pre>Coverage: '+e(json.dumps(report['coverage'],indent=2))+'</pre></section><section class="panel"><h2>Matched comparison</h2><p>Intervals are 95% paired percentile bootstrap estimates, not adjusted for multiple slices. Small or constant samples remain uncertain.</p><table><tr><th>Slice</th><th>Pairs</th><th>Baseline</th><th>Candidate</th><th>Improvement</th><th>95% interval</th><th>Signal</th></tr>'+stats+'</table></section><section class="panel"><h2>Item-level evidence</h2><table><tr><th>ID</th><th>Slice</th><th>Baseline</th><th>Candidate</th><th>Raw delta</th><th>Improvement</th></tr>'+rows+'</table></section><details><summary>Full audit record</summary><pre>'+e(json.dumps(report,indent=2))+'</pre></details></html>'
