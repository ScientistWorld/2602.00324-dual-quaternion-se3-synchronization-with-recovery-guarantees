"""Populate gym-scale numbers in scoring/reference.json from the final reference run.

Results come from the canonical public-slice scores (reference and fixed
comparators only). Paper-reported values under keys starting with '_' are
never modified. The evaluator ranking snapshots must equal reference.json.
"""
import json
from pathlib import Path

reference = json.loads(Path('scoring/reference.json').read_text())
train = json.loads(Path('scoring/scores_train.json').read_text())
for exp, value in reference['experiments'].items():
    results = train['experiments'][exp]['results']
    value['results'] = {name: {'type': 'proposed' if name == 'dqgpm' else 'baseline', **metrics}
                        for name, metrics in results.items()}
Path('scoring/reference.json').write_text(json.dumps(reference, indent=2) + '\n')
for side in ('train', 'test'):
    config = json.loads(Path(f'eval/{side}/ranking.json').read_text())
    assert config == {'experiments': {k: {'weight': v['weight'], 'metrics': v['metrics']}
                                      for k, v in reference['experiments'].items()}}, side
print('frozen', {e: sorted(v['results']) for e, v in reference['experiments'].items()})
