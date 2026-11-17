import argparse
import json
import sys
from . import SnapshotError, load, compare

def main():
    parser = argparse.ArgumentParser(description='Diff two local evidence snapshots. No model or network calls.')
    parser.add_argument('before')
    parser.add_argument('after')
    parser.add_argument('--output', help='Create a new JSON file; never overwrite an existing file.')
    args = parser.parse_args()
    try:
        report = json.dumps(compare(load(args.before), load(args.after)), indent=2, ensure_ascii=False) + '\n'
        if args.output:
            with open(args.output, 'x', encoding='utf-8') as stream:
                stream.write(report)
        else:
            print(report, end='')
    except (SnapshotError, OSError, UnicodeError) as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__':
    sys.exit(main())
