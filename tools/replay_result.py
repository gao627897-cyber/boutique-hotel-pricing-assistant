"""Display an actual saved evaluation decision; explicitly label the replay."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description='Replay an actual saved result; zero model/API calls.')
parser.add_argument('--case-id',required=True)
parser.add_argument('--run',choices=('first','refined'),default='refined',
                    help='Select the actual recorded first or refined evaluation.')
args=parser.parse_args()
try:
    directory='results/stage4/openrouter_run_01' if args.run=='first' else 'results/refinement_01/openrouter_run_01'
    lines=(ROOT/directory/'predictions.jsonl').read_text().splitlines()
    rows=[json.loads(line) for line in lines]
    row=next(row for row in rows if row['case_id']==args.case_id)
except (OSError,ValueError,StopIteration):
    print('No saved result for this case. Complete the real evaluation first.',file=sys.stderr)
    raise SystemExit(2)
print('RECORDED EVALUATION REPLAY — no new API call; audit timestamps/calls belong to the original run.')
print(json.dumps(row,ensure_ascii=False,indent=2))
