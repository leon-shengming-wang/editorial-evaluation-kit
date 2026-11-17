"""Reproduce explicitly synthetic demonstration artifacts."""
import json
from pathlib import Path
from splitguard import load, audit, render
report = audit(load('examples/records.jsonl'), threshold=0.5)
report['dataset_notice'] = 'SYNTHETIC DEMONSTRATION: authored fictional examples, not measured model outputs or private platform data.'
Path('reports').mkdir(exist_ok=True)
Path('reports/synthetic-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
Path('reports/synthetic-audit.html').write_text(render(report), encoding='utf-8')
