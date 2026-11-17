"""Export a label-free Markdown worksheet, not a secure assessment system."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from .core import CATEGORIES, DatasetError, load


def literal(value):
    """Fence untrusted example text without interpreting HTML or Markdown."""
    longest = max((len(x) for x in re.findall(r'`+', value)), default=0)
    fence = '`' * max(3, longest + 1)
    return fence + '\n' + value + '\n' + fence


def input_fingerprint(record):
    """Identify the displayed input, independent of hidden reference decisions."""
    visible = {key: record[key] for key in ('id', 'category', 'prompt', 'source', 'responses')}
    payload = json.dumps(visible, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def worksheet(records, categories=None):
    selected = [r for r in records if not categories or r['category'] in categories]
    if not selected:
        raise ValueError('no cases match the selected categories')
    parts = ['# Independent practice worksheet',
             'Synthetic, AI-assisted practice. No recording or original non-English text is supplied. '
             'This is not a hiring test or a measure of language proficiency. '
             'Reference judgments are intentionally omitted here but remain visible in the repository.',
             'Read the prompt and source before comparing responses. Record your own judgment before '
             'opening the reference walkthrough. A preference is not approval for publication. '
             'Use abstain when the central question cannot be resolved from the supplied evidence.']
    for r in selected:
        parts += ['## ' + r['id'] + ' / ' + r['category'],
                  'Input fingerprint (SHA-256): `' + input_fingerprint(r) + '`',
                  '### Task', literal(r['prompt']), '### Supplied source', literal(r['source']),
                  '### Response A', literal(r['responses']['A']),
                  '### Response B', literal(r['responses']['B']),
                  '### Your review (leave blank until you have reviewed)',
                  '- Decision (A / B / tie / abstain):\n- Exact evidence:\n- Main defect in each response:\n'
                  '- What remains unknown:\n- Is either response ready to use?\n- Proposed correction:\n'
                  '- What evidence would change your decision:']
    return '\n\n'.join(parts) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset')
    parser.add_argument('--category', action='append', choices=CATEGORIES)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        output = Path(args.output)
        if output.resolve() == Path(args.dataset).resolve():
            raise ValueError('output must not overwrite input')
        text = worksheet(load(args.dataset), args.category)
        # Exclusive creation protects previous practice notes and other local files.
        with output.open('x', encoding='utf-8') as f:
            f.write(text)
    except (OSError, ValueError, DatasetError) as exc:
        parser.exit(1, 'Practice export failed: ' + str(exc) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
