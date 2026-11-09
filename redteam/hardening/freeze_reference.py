"""Populate gym-scale numeric targets from the final raw reference runs.
Paper-reported values under _paper_reported are never modified here.
"""
import json
from pathlib import Path
reference=json.loads(Path('scoring/reference.json').read_text())
train=json.loads(Path('scoring/scores_train.json').read_text())
for exp,value in reference['experiments'].items():
    results=train['experiments'][exp]['results']
    for name,definition in value['results'].items():
        value['results'][name]={'type':definition['type'],**results[name]}
Path('scoring/reference.json').write_text(json.dumps(reference,indent=2)+'\n')
# Ranking coefficients are immutable evaluator snapshots, identical to reference.
for side in ('train','test'):
    config=json.loads(Path(f'eval/{side}/ranking.json').read_text())
    assert config=={'experiments':{k:{'weight':v['weight'],'metrics':v['metrics']} for k,v in reference['experiments'].items()}}
