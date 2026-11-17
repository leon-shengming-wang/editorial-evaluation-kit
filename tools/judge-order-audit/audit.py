#!/usr/bin/env python3
"""Audit imported order-swapped judge decisions. No inference or network calls."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import sys

MAX_BYTES = 8 * 1024 * 1024
CATEGORIES = ('consistent', 'flipped', 'tie', 'abstain', 'missing')


def fail(message):
    raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def keys(obj, required, optional, where):
    if not isinstance(obj, dict):
        fail(where + ' must be an object')
    if set(obj) - set(required) - set(optional) or set(required) - set(obj):
        fail(where + ': missing required or unknown fields')


def text(value, where, limit=20000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        fail(where + ': expected nonempty string within length limit')
    if any(ord(c) < 32 and c not in '\n\r\t' for c in value):
        fail(where + ': control characters are not allowed')
    if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        fail(where + ': unpaired Unicode surrogate')


def validate(data):
    keys(data, ('schema_version', 'data_kind', 'judge', 'rubric', 'cases'), ('notes',), 'input')
    if type(data['schema_version']) is not int or data['schema_version'] != 1:
        fail('schema_version must be integer 1')
    if data['data_kind'] not in ('synthetic', 'imported'):
        fail('data_kind must be synthetic or imported')
    text(data['judge'], 'judge', 300)
    text(data['rubric'], 'rubric', 2000)
    if 'notes' in data:
        text(data['notes'], 'notes')
    cases = data['cases']
    if not isinstance(cases, list) or not 1 <= len(cases) <= 10000:
        fail('cases must contain 1–10000 records')
    seen = set()
    for i, case in enumerate(cases):
        label = 'case ' + str(i + 1)
        keys(case, ('id', 'original', 'swapped'), ('prompt', 'answer_a', 'answer_b'), label)
        text(case['id'], label + '.id', 200)
        if case['id'] in seen:
            fail('Duplicate case id: ' + case['id'])
        seen.add(case['id'])
        for key in ('prompt', 'answer_a', 'answer_b'):
            if key in case:
                text(case[key], label + '.' + key)
        for order in ('original', 'swapped'):
            run = case[order]
            if run is None:
                continue
            keys(run, ('verdict',), ('reason', 'run_id'), label + '.' + order)
            if not isinstance(run['verdict'], str) or run['verdict'] not in ('first', 'second', 'tie', 'abstain'):
                fail(label + '.' + order + ': verdict must be first, second, tie or abstain')
            for key in ('reason', 'run_id'):
                if key in run:
                    text(run[key], label + '.' + order + '.' + key)
    return data


def loads(raw):
    if len(raw.encode('utf-8')) > MAX_BYTES:
        fail('Input exceeds 8 MB')
    try:
        return validate(json.loads(raw, object_pairs_hook=unique_object,
                                   parse_constant=lambda v: fail('Non-finite JSON value: ' + v)))
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('Invalid JSON: ' + str(exc)) from exc


def normalize(run, swapped=False):
    if run is None:
        return None
    verdict = run['verdict']
    if verdict in ('tie', 'abstain'):
        return verdict
    return {'first': 'B' if swapped else 'A', 'second': 'A' if swapped else 'B'}[verdict]


def classify(a, b):
    if a is None or b is None:
        return 'missing', 'Both runs missing' if a is None and b is None else 'One run missing'
    if 'abstain' in (a, b):
        return 'abstain', 'Both abstained' if a == b else 'At least one abstention'
    if 'tie' in (a, b):
        return 'tie', 'Both tied' if a == b else 'Tie versus decisive preference'
    if a == b:
        return 'consistent', 'Same original answer preferred in both orders'
    return 'flipped', 'Different original answers preferred after order reversal'


def ratio(n, d):
    return None if d == 0 else round(n / d, 6)


def analyze(data):
    validate(data)
    rows = []
    counts = dict.fromkeys(CATEGORIES, 0)
    observed = decisive_runs = first_picks = complete = both_tied = tie_changed = 0
    for case in data['cases']:
        a, b = normalize(case['original']), normalize(case['swapped'], True)
        category, detail = classify(a, b)
        counts[category] += 1
        complete += case['original'] is not None and case['swapped'] is not None
        both_tied += a == b == 'tie'
        tie_changed += category == 'tie' and a != b
        for run in (case['original'], case['swapped']):
            if run is not None:
                observed += 1
                decisive_runs += run['verdict'] in ('first', 'second')
                first_picks += run['verdict'] == 'first'
        rows.append({**case, 'normalized_original': a, 'normalized_swapped': b,
                     'category': category, 'detail': detail})
    n = len(rows)
    eligible = counts['consistent'] + counts['flipped']
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=True,
                                      separators=(',', ':')).encode()).hexdigest()
    return {'report_version': 1, 'input_sha256': digest, 'data_kind': data['data_kind'],
            'judge': data['judge'], 'rubric': data['rubric'], 'notes': data.get('notes', ''),
            'summary': {'cases': n, 'expected_runs': n * 2, 'observed_runs': observed,
                        'complete_pairs': complete, 'complete_pair_rate': ratio(complete, n),
                        'decisive_pairs': eligible, 'categories': counts,
                        'consistent_rate_decisive_pairs': ratio(counts['consistent'], eligible),
                        'flip_rate_decisive_pairs': ratio(counts['flipped'], eligible),
                        'both_tied': both_tied, 'tie_changed': tie_changed,
                        'first_position_picks': first_picks, 'decisive_runs': decisive_runs,
                        'first_position_pick_rate': ratio(first_picks, decisive_runs)},
            'cases': rows}


def render(report):
    esc = lambda x: html.escape(str(x), quote=True)
    s = report['summary']
    percent = lambda x: 'N/A' if x is None else f'{x:.1%}'
    cards = ''.join(f'<div class="card"><b>{esc(value)}</b><span>{esc(label)}</span></div>' for label, value in (
        ('Cases', s['cases']), ('Complete pairs', f"{s['complete_pairs']} / {s['cases']}"),
        ('Flips / decisive pairs', f"{s['categories']['flipped']} / {s['decisive_pairs']}"),
        ('Flip rate, decisive pairs', percent(s['flip_rate_decisive_pairs']))))
    rows = []
    for case in report['cases']:
        def run(order):
            value = case[order]
            return 'Missing' if value is None else esc(value['verdict'])
        details = ''.join(f'<h4>{esc(key.replace("_", " ").title())}</h4><pre>{esc(case[key])}</pre>'
                          for key in ('prompt', 'answer_a', 'answer_b') if key in case)
        for order in ('original', 'swapped'):
            if case[order] is not None:
                details += f'<h4>{order.title()} run record</h4><pre>{esc(json.dumps(case[order], indent=2, ensure_ascii=False))}</pre>'
        rows.append(f'<tr><th scope="row">{esc(case["id"])}</th><td>{run("original")} → {esc(case["normalized_original"] or "missing")}</td><td>{run("swapped")} → {esc(case["normalized_swapped"] or "missing")}</td><td><strong>{esc(case["category"])}</strong><br>{esc(case["detail"])}</td></tr><tr><td colspan="4"><details><summary>Inspect input evidence</summary>{details or "No run evidence supplied."}</details></td></tr>')
    counts = ' · '.join(f'{key}: {value}' for key, value in s['categories'].items())
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Judge Order Audit</title><style>
body{{margin:0;background:#f6f5f0;color:#192f2c;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:40px 24px}}h1{{font-size:clamp(32px,6vw,56px);letter-spacing:-2px;margin:10px 0}}.kicker{{text-transform:uppercase;letter-spacing:3px;font-size:12px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:28px 0}}.card{{background:white;border:1px solid #d6dfda;border-radius:14px;padding:22px}}.card b{{display:block;font-size:30px}}.card span{{font-size:13px}}.notice{{background:#e4eee8;padding:20px;border-left:4px solid #456c59}}.table{{overflow:auto}}table{{width:100%;border-collapse:collapse;background:white}}th,td{{text-align:left;padding:14px;vertical-align:top;border-bottom:1px solid #ddd}}thead{{background:#193f36;color:white}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.6 monospace}}summary{{cursor:pointer}}footer{{margin-top:32px;font-size:13px;color:#53645d}}code{{overflow-wrap:anywhere}}</style><main>
<div class="kicker">Evaluation reliability · local audit</div><h1>Does the preference survive a swap?</h1><p>Judge: {esc(report['judge'])}<br>Rubric: {esc(report['rubric'])}</p>
<p class="notice"><strong>{esc(report['data_kind'].upper())} INPUT</strong> · This report audits supplied decisions. No model was called. Order stability does not establish correctness or human agreement. A flip is a review signal, not proof of causal position bias.</p>
{cards}<h2>Coverage before conclusions</h2><p>{esc(counts)}</p><p>Observed runs: {s['observed_runs']} / {s['expected_runs']}. Both tied: {s['both_tied']}. Tie versus decisive preference: {s['tie_changed']}. First-position picks: {s['first_position_picks']} / {s['decisive_runs']} decisive runs ({percent(s['first_position_pick_rate'])}); this includes incomplete pairs and is descriptive only.</p>
<p>Original order is [A, B]; swapped order is [B, A]. “First” and “second” are displayed positions, not answer identities. Missing takes precedence over abstain, then tie; only two decisive preferences enter the flip-rate denominator.</p>
<h2>Pair-by-pair evidence</h2><div class="table"><table><thead><tr><th>Case</th><th>Original → identity</th><th>Swapped → identity</th><th>Outcome</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>Review next</h2><p>Inspect flipped and tie-changed cases with the original rubric. Recover missing runs before comparing datasets. Keep model version, prompt, sampling and rubric fixed across paired runs, and repeat with independent runs before attributing changes to ordering.</p><p>{esc(report['notes'])}</p><footer>Deterministic input fingerprint: <code>{report['input_sha256']}</code><br>No scripts, remote fonts, analytics or network dependencies. Imported text is escaped.</footer></main></html>'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='Strict UTF-8 JSON input')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--force', action='store_true', help='Replace report.json/report.html if present')
    args = parser.parse_args(argv)
    try:
        with args.input.open('rb') as handle:
            raw = handle.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            fail('Input exceeds 8 MB')
        report = analyze(loads(raw.decode('utf-8')))
        outputs = {args.output_dir / 'report.json': json.dumps(report, indent=2, ensure_ascii=False) + '\n',
                   args.output_dir / 'report.html': render(report)}
        if args.input.resolve() in (p.resolve() for p in outputs):
            fail('Output would overwrite the input')
        if not args.force and any(p.exists() for p in outputs):
            fail('Report already exists; choose another output directory or use --force')
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for path, content in outputs.items():
            with path.open('w' if args.force else 'x', encoding='utf-8') as handle:
                handle.write(content)
        print(f"Audited {report['summary']['cases']} cases. Reports: {args.output_dir}")
        return 0
    except (ValueError, OSError, UnicodeError) as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
