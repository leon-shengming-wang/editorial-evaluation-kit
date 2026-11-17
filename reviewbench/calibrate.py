"""CLI for an actual local review, never fabricated reviewer activity."""
import argparse
import json
import sqlite3
import sys
from .audit import AuditStore
from .core import DatasetError, load

def main(argv=None):
    parser=argparse.ArgumentParser(description='Keep a local, append-only review history. Do not upload private review data.')
    parser.add_argument('--database', required=True)
    commands=parser.add_subparsers(dest='command', required=True)
    seed=commands.add_parser('import', help='Import validated synthetic cases without creating reviews')
    seed.add_argument('dataset')
    review=commands.add_parser('review', help='Record a review you actually performed')
    review.add_argument('case_id'); review.add_argument('--reviewer',required=True)
    review.add_argument('--winner',choices=['A','B','tie','abstain'],required=True)
    review.add_argument('--reason',required=True)
    history=commands.add_parser('history'); history.add_argument('case_id')
    commands.add_parser('disagreements',help='Show latest decisions differing from authored references, not accuracy')
    args=parser.parse_args(argv)
    try:
        # Validate before touching the database when importing.
        records=load(args.dataset) if args.command=='import' else None
        with AuditStore(args.database) as store:
            if args.command=='import':
                store.import_cases(records); result={'imported_cases':len(records),'reviews_created':0}
            elif args.command=='review':
                result={'sequence':store.add_review(args.case_id,args.reviewer,args.winner,args.reason)}
            elif args.command=='history':
                keys=('sequence','reviewer','winner','reason','recorded_at')
                result=[dict(zip(keys,row)) for row in store.history(args.case_id)]
            else:
                keys=('case_id','reviewer','reference_winner','review_winner','reason')
                result=[dict(zip(keys,row)) for row in store.disagreements()]
        print(json.dumps(result,indent=2))
        return 0
    except (DatasetError,ValueError,OSError,UnicodeError,sqlite3.Error) as exc:
        print('Calibration failed: '+str(exc),file=sys.stderr)
        return 1

if __name__=='__main__': sys.exit(main())
