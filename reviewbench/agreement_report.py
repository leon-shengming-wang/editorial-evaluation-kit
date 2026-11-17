"""Escaped offline report for the pairwise audit."""
from html import escape
from .agreement import LABELS


def render(result, *, title='Pairwise review audit', provenance='User-supplied local ratings; provenance not verified'):
    def e(value): return escape(str(value), quote=True)
    def number(value): return 'Not defined' if value is None else format(value, '.3f')
    left, right = result['reviewers']
    matrix = '<table><caption>Rows: ' + e(left) + ' / columns: ' + e(right) + '</caption><thead><tr><th scope="col">Decision</th>'
    matrix += ''.join('<th scope="col">' + e(x) + '</th>' for x in LABELS) + '</tr></thead><tbody>'
    for a in LABELS:
        matrix += '<tr><th scope="row">' + e(a) + '</th>'
        for b in LABELS:
            matrix += '<td' + (' class="match"' if a == b else '') + '>' + str(result['confusion_matrix'][a][b]) + '</td>'
        matrix += '</tr>'
    matrix += '</tbody></table>'
    queue = ''
    for item in result['disagreements']:
        queue += '<article><h3>' + e(item['case_id']) + '</h3><div class="pair">'
        for side, reviewer in [('left', left), ('right', right)]:
            queue += '<section><h4>' + e(reviewer) + ' · ' + e(item[side + '_label']) + '</h4><p>' + e(item[side + '_reason']) + '</p></section>'
        queue += '</div><p class="note">' + e(item['action']) + '</p></article>'
    if not queue: queue = '<p>No differing labels among shared cases. This does not establish correctness.</p>'
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>''' + e(title) + '''</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#101418;color:#eef3f4;font:17px/1.6 system-ui,sans-serif}main{max-width:1080px;margin:auto;padding:50px 24px}h1{font-size:clamp(32px,5vw,60px);line-height:1.08;letter-spacing:-.04em;margin:18px 0}h2{margin-top:44px}h3,h4{margin-top:0}.eyebrow{color:#82d9c1;letter-spacing:.16em;text-transform:uppercase;font-size:12px}.intro{max-width:740px;color:#b6c4ca}.stats,.pair{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.stats>div,article{border:1px solid #34434a;border-radius:14px;padding:24px;margin-top:20px;background:#171e23}.stats strong{display:block;font-size:32px;color:#82d9c1}.pair{grid-template-columns:repeat(2,1fr)}.pair section{background:#202a31;border-radius:8px;padding:18px}.note,caption{color:#b6c4ca}table{border-collapse:collapse;width:100%;margin-top:24px}th,td{padding:14px;text-align:center;border:1px solid #34434a}.match{background:#203b35}caption{text-align:left;padding-bottom:10px}p{white-space:pre-wrap;overflow-wrap:anywhere}.scope{border-left:3px solid #82d9c1;padding-left:18px}footer{margin-top:50px;color:#b6c4ca;font-size:14px}@media(max-width:640px){.stats,.pair{grid-template-columns:1fr}main{padding:28px 16px}}@media print{body{background:white;color:black}.stats>div,article,.pair section,.match{background:white;color:black}article{break-inside:avoid}.intro,.note,footer,caption{color:#333}}
</style><main><div class="eyebrow">ReviewBench / calibration lab</div><h1>''' + e(title) + '''</h1>
<p class="intro">Compare decisions without treating agreement as truth. Inspect coverage first, then read the reasons behind each disagreement.</p>
<p class="scope">''' + e(provenance) + '''</p><div class="stats"><div>Shared cases<strong>''' + str(result['shared_cases']) + '''</strong></div><div>Exact agreement<strong>''' + number(result['observed_agreement']) + '''</strong></div><div>Cohen's kappa<strong>''' + number(result['cohens_kappa']) + '''</strong></div></div>
<h2>Coverage before conclusions</h2><p>Only ''' + e(left) + ': ' + e(', '.join(result['left_only_cases']) or 'none') + '\nOnly ' + e(right) + ': ' + e(', '.join(result['right_only_cases']) or 'none') + '''</p><p>Kappa status: ''' + e(result['kappa_status']) + '''. Missing ratings are excluded; abstain is a real category, not a missing value.</p>
<h2>Where decisions align</h2>''' + matrix + '''<h2>Disagreement review queue</h2>''' + queue + '''<h2>Limits</h2><ul>''' + ''.join('<li>' + e(x) + '</li>' for x in result['limitations']) + '''</ul><footer>AI-assisted portfolio demonstration. No platform endorsement, hiring outcome or reliability claim. No external scripts, fonts, analytics or network requests.</footer></main></html>'''
