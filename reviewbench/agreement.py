"""Read-only pairwise agreement audit; agreement is not accuracy."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3

LABELS = ('A', 'B', 'tie', 'abstain')


def compare(rows, reviewer_a, reviewer_b):
    """Compare latest ratings on shared cases; retain abstentions in the denominator.

    rows: (case_id, reviewer, winner, reason). Duplicate case/reviewer pairs fail
    rather than silently selecting an arbitrary revision.
    """
    if not reviewer_a.strip() or not reviewer_b.strip() or reviewer_a == reviewer_b:
        raise ValueError('choose two different nonempty reviewer IDs')
    ratings = {reviewer_a: {}, reviewer_b: {}}
    for case_id, reviewer, winner, reason in rows:
        if reviewer not in ratings:
            continue
        if winner not in LABELS:
            raise ValueError('invalid label for ' + str(case_id))
        if case_id in ratings[reviewer]:
            raise ValueError('duplicate rating: ' + str(case_id))
        ratings[reviewer][case_id] = (winner, reason)
    left, right = ratings[reviewer_a], ratings[reviewer_b]
    shared = sorted(left.keys() & right.keys())
    counts_a, counts_b = Counter(), Counter()
    matrix = {a: {b: 0 for b in LABELS} for a in LABELS}
    queue = []
    equal = 0
    for case in shared:
        a, ra = left[case]
        b, rb = right[case]
        counts_a[a] += 1
        counts_b[b] += 1
        matrix[a][b] += 1
        equal += a == b
        if a != b:
            queue.append({'case_id': case, 'left_label': a, 'right_label': b,
                          'left_reason': ra, 'right_reason': rb,
                          'action': 'Review the source and rubric; do not assume either reviewer is wrong.'})
    n = len(shared)
    observed = equal / n if n else None
    expected = sum(counts_a[x] * counts_b[x] for x in LABELS) / (n * n) if n else None
    kappa = ((observed - expected) / (1 - expected)) if n and expected < 1 else None
    return {'reviewers': [reviewer_a, reviewer_b], 'shared_cases': n,
            'left_only_cases': sorted(left.keys() - right.keys()),
            'right_only_cases': sorted(right.keys() - left.keys()),
            'exact_agreements': equal, 'observed_agreement': observed,
            'chance_agreement': expected, 'cohens_kappa': kappa,
            'kappa_status': 'defined' if kappa is not None else
                ('no_shared_cases' if not n else 'constant_identical_labels'),
            'confusion_matrix': matrix, 'disagreements': queue,
            'limitations': ['All four labels, including abstain, count as nominal categories.',
                            'Only latest ratings on shared cases are compared; missing ratings are not disagreements.',
                            'Small or selected samples are descriptive, not evidence of reviewer reliability or accuracy.',
                            'Ratings and reasons may contain personal information. Inspect before sharing.']}


def audit(path, reviewer_a, reviewer_b):
    """Open an existing database read-only; never create or modify its schema."""
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError('database must be a file')
    conn = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    try:
        rows = conn.execute('SELECT case_id,reviewer,winner,reason FROM latest_reviews').fetchall()
    finally:
        conn.close()
    return compare(rows, reviewer_a, reviewer_b)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database')
    parser.add_argument('reviewer_a')
    parser.add_argument('reviewer_b')
    outputs = parser.add_mutually_exclusive_group()
    outputs.add_argument('--output', help='new JSON file; existing files are never overwritten')
    outputs.add_argument('--html', help='new offline HTML report; existing files are never overwritten')
    args = parser.parse_args(argv)
    try:
        result = audit(args.database, args.reviewer_a, args.reviewer_b)
        if args.html:
            from .agreement_report import render
            report = render(result)
        else:
            report = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        if args.output or args.html:
            with Path(args.output or args.html).open('x', encoding='utf-8') as out:
                out.write(report)
        else:
            print(report, end='')
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(1, 'Agreement audit failed: ' + str(exc) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
