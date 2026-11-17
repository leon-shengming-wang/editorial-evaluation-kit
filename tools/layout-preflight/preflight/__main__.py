import argparse
import json
import sys
import os
import tempfile
from pathlib import Path
from .core import inspect
from .render import html,svg

def strict_object(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError('duplicate JSON key: '+key)
        result[key]=value
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description='Check a design specification, not rendered artwork.')
    p.add_argument('spec',type=Path); p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        spec=json.loads(args.spec.read_text(encoding='utf-8'),object_pairs_hook=strict_object)
        findings=inspect(spec)
        output=args.output.resolve(); source=args.spec.resolve()
        outputs=[output/'report.html',output/'specimen.svg',output/'findings.json']
        if source in outputs: raise ValueError('output would overwrite input')
        args.output.mkdir(parents=True,exist_ok=True)
        payloads=[html(spec,findings),svg(spec),json.dumps(findings,indent=2)+'\n']
        for path in outputs:
            if path.exists() and not path.is_file(): raise ValueError('output is not a regular file: '+str(path))
        staged=[]
        try:
            for path,payload in zip(outputs,payloads):
                with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=str(output),delete=False) as temporary:
                    staged.append((Path(temporary.name),path));temporary.write(payload)
            for temporary,path in staged: os.replace(str(temporary),str(path))
        finally:
            for temporary,_ in staged:
                if temporary.exists(): temporary.unlink()
        print('{} findings; inspect {}'.format(len(findings),output/'report.html'))
        return 1 if any(f['severity']=='error' for f in findings) else 0
    except (OSError,UnicodeError,ValueError) as exc:
        print('Preflight failed: '+str(exc),file=sys.stderr); return 2

if __name__=='__main__': sys.exit(main())
