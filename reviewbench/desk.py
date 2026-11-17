"""Generate a private, offline review desk. It never sends reviews to a server."""
import argparse
import json
from pathlib import Path
from .core import DatasetError, load
from .practice import input_fingerprint


def payload(records):
    """Keep references out of the page, reducing answer anchoring."""
    return [{**{k: r[k] for k in ('id', 'category', 'prompt', 'source', 'responses')},
             'fingerprint': input_fingerprint(r)} for r in records]


def script_json(value):
    return json.dumps(value, ensure_ascii=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def render(records):
    assets = Path(__file__).parent / 'assets'
    template = (assets / 'desk.html').read_text(encoding='utf-8')
    return template.replace('/*__CODE__*/', (assets / 'desk.js').read_text(encoding='utf-8')).replace('/*__DATA__*/', script_json(payload(records)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset')
    parser.add_argument('--output', required=True, help='New HTML file; existing files are protected')
    args = parser.parse_args(argv)
    try:
        text = render(load(args.dataset))
        with Path(args.output).open('x', encoding='utf-8') as out:
            out.write(text)
    except (ValueError, OSError, DatasetError) as exc:
        parser.exit(1, 'Review desk export failed: ' + str(exc) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
