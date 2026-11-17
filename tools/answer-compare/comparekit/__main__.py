import argparse
import json
import sys
from pathlib import Path
from .core import InputError, MAX_BYTES, analyze, parse

def main():
    p = argparse.ArgumentParser(description='Compare answer pairs against explicit constraints. No API key or network required.')
    p.add_argument('input', nargs='?', help='JSON or JSONL input')
    p.add_argument('--output', help='New JSON output path; existing files are never overwritten')
    p.add_argument('--serve', action='store_true', help='Start the local review UI')
    p.add_argument('--port', type=int, default=8768)
    args = p.parse_args()
    if args.serve:
        from .server import serve
        serve(args.port)
        return
    if not args.input:
        p.error('provide input or --serve')
    try:
        with open(args.input, 'rb') as source:
            raw = source.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise InputError('Input exceeds 2 MB.')
        result = analyze(parse(raw.decode('utf-8')))
        encoded = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.output:
            with open(args.output, 'x', encoding='utf-8') as stream:
                stream.write(encoded)
        else:
            print(encoded, end='')
    except (InputError, OSError, UnicodeError) as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        sys.exit(2)

if __name__ == '__main__':
    main()
