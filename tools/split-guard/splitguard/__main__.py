import argparse
import json
import sys
from pathlib import Path
from . import InputError, load, audit, render

def main():
    p=argparse.ArgumentParser(description='Audit cross-split exact and token-shingle text overlap locally.')
    p.add_argument('input');p.add_argument('--threshold',type=float,default=.7);p.add_argument('--shingle-size',type=int,default=3)
    p.add_argument('--json',dest='json_path');p.add_argument('--html',dest='html_path')
    args=p.parse_args()
    try:
        paths=[Path(x) for x in (args.json_path,args.html_path) if x]
        if len(set(p.resolve() for p in paths))!=len(paths):raise InputError('Output paths must differ.')
        for path in paths:
            if path.exists():raise InputError('Output already exists: '+str(path))
        report=audit(load(args.input),args.threshold,args.shingle_size)
        encoded=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
        for dest,data in ((args.json_path,encoded),(args.html_path,render(report))):
            if dest:
                with open(dest,'x',encoding='utf-8') as stream:stream.write(data)
        if not paths:print(encoded,end='')
        return 0
    except (InputError,OSError,UnicodeError) as exc:
        print('Error: '+str(exc),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
