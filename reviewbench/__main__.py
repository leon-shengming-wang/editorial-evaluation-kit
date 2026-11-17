"""Run with python3 -m reviewbench DATASET [--html PATH] [--json PATH]."""
import argparse
import json
import sys
import os
import tempfile
from pathlib import Path
from .core import DatasetError, load, summarize
from .report import render

def main(argv=None):
    parser = argparse.ArgumentParser(description='Validate synthetic A/B review records and generate an auditable report.')
    parser.add_argument('dataset', type=Path)
    parser.add_argument('--html', type=Path)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args(argv)
    outputs = [p for p in (args.html, args.json) if p is not None]
    if len({p.resolve() for p in outputs + [args.dataset]}) != len(outputs) + 1:
        parser.error('input and output paths must be different')
    try:
        records = load(args.dataset)
        summary = summarize(records)
        payloads = []
        if args.html: payloads.append((args.html, render(records)))
        if args.json: payloads.append((args.json, json.dumps(summary, indent=2) + '\n'))
        # Preflight every destination and stage all bytes before replacing any file.
        for path, _ in payloads:
            if not path.parent.is_dir(): raise OSError('output directory does not exist: ' + str(path.parent))
            if path.exists() and not path.is_file(): raise OSError('output is not a regular file: ' + str(path))
        staged = []
        try:
            for path, content in payloads:
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=str(path.parent), delete=False) as temp:
                    staged.append((Path(temp.name), path))
                    temp.write(content)
            for temporary, destination in staged:
                os.replace(str(temporary), str(destination))
        finally:
            for temporary, _ in staged:
                if temporary.exists(): temporary.unlink()
    except (DatasetError, OSError, UnicodeError) as exc:
        print('ReviewBench failed: ' + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2))
    return 0

if __name__ == '__main__':
    sys.exit(main())
