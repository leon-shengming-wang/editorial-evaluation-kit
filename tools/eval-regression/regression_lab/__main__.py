import argparse
import json
import sys
from pathlib import Path
from . import InputError, load, compare, render

def main():
    p=argparse.ArgumentParser(description='Compare imported paired evaluation scores; no model calls.')
    p.add_argument('baseline');p.add_argument('candidate')
    p.add_argument('--json',dest='json_path');p.add_argument('--html',dest='html_path')
    p.add_argument('--resamples',type=int,default=2000);p.add_argument('--seed',type=int,default=17)
    args=p.parse_args()
    try:
        paths=[Path(x).resolve() for x in (args.json_path,args.html_path) if x]
        if len(set(paths))!=len(paths):raise InputError('Output paths must be distinct.')
        if any(x.exists() for x in paths):raise InputError('Output already exists; use new paths.')
        report=compare(load(args.baseline),load(args.candidate),args.resamples,args.seed)
        for path,content in ((args.json_path,json.dumps(report,indent=2)+'\n'),(args.html_path,render(report))):
            if path:
                with open(path,'x',encoding='utf-8') as stream:stream.write(content)
        if not paths:print(json.dumps(report,indent=2))
    except (InputError,OSError,UnicodeError) as exc:
        print('Error: '+str(exc),file=sys.stderr);return 2
    return 0
if __name__=='__main__':sys.exit(main())
