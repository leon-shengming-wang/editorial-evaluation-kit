"""Generate a deterministic, explicitly simulated audit. No real reviewer data."""
from pathlib import Path
import json
from reviewbench.agreement import compare
from reviewbench.agreement_report import render

rows = [
 ('demo-01', 'simulated-left', 'A', 'A preserves the source quantity; B changes applications into approvals.'),
 ('demo-01', 'simulated-right', 'A', 'The metric in A matches the source.'),
 ('demo-02', 'simulated-left', 'B', 'B preserves the uncertainty qualifier.'),
 ('demo-02', 'simulated-right', 'tie', 'Both omit a required detail. Revisit whether the qualifier outweighs that omission.'),
 ('demo-03', 'simulated-left', 'abstain', 'The transcript omits the word needed to decide.'),
 ('demo-03', 'simulated-right', 'abstain', 'Missing evidence prevents a choice.'),
 ('demo-04', 'simulated-left', 'A', 'A follows the requested word limit.'),
 ('demo-04', 'simulated-right', 'B', 'B retains the safety qualification. Revisit competing instruction priorities.'),
 ('demo-05', 'simulated-left', 'tie', 'No material difference in the supplied text.'),
 ('demo-05', 'simulated-right', 'tie', 'Both responses satisfy the same constraints.'),
 ('demo-06', 'simulated-left', 'A', 'Unpaired demonstration record; excluded from agreement calculations.'),
]
if __name__ == '__main__':
    result = compare(rows, 'simulated-left', 'simulated-right')
    result['provenance'] = 'All ratings and reasons are AI-authored simulations, not real human review or model measurements.'
    Path('reports/agreement-demo.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    Path('reports/agreement-demo.html').write_text(render(result, title='Agreement is not accuracy.', provenance=result['provenance']), encoding='utf-8')
