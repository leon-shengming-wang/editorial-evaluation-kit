import argparse
import json
from pathlib import Path
import sys
from . import InputError, evaluate, load, render_html

def main():
    parser = argparse.ArgumentParser(description='Score local qrels and explicit ordered retrieval runs.')
    parser.add_argument('qrels'); parser.add_argument('run')
    parser.add_argument('--k', type=int, default=10)
    parser.add_argument('--output-dir', required=True, help='New directory for report.json and report.html; must not exist')
    args = parser.parse_args()
    try:
        report = evaluate(load(args.qrels), load(args.run), args.k)
        json_text = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
        html_text = render_html(report)
        target = Path(args.output_dir)
        target.mkdir()  # exclusive; never alter an existing directory
        (target/'report.json').write_text(json_text, encoding='utf-8')
        (target/'report.html').write_text(html_text, encoding='utf-8')
        print('Created ' + str(target/'report.json') + ' and ' + str(target/'report.html'))
        return 0
    except (InputError, OSError, UnicodeError) as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        return 2

if __name__ == '__main__': sys.exit(main())
