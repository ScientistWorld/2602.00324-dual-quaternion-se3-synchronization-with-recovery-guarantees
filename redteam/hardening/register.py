"""Register all controls for ONE joint hardening job; generated manifests ignored."""
import json
from pathlib import Path

CONTROL_COMMANDS={
'baseline_matrix_eig':['python3','-m','baseline.matrix_eig'],
'reference_seed1':['python3','-m','method.solve','--seed','1'],
'reference_seed2':['python3','-m','method.solve','--seed','2'],
'weaker_spectral':['python3','-m','method.solve','--stage','spectral'],
'weaker_one_iteration':['python3','-m','method.solve','--stage','spectral','--init-max-iter','1'],
}
MODES=('better_noise_aware','rebuild_answers','rewrite_truth','bruteforce_seed_bank','one_pose','select_trials','easier_inputs','replace_baseline','compensate_failure','nan','negative_scalar')
for mode in MODES:
    name=mode if mode=='better_noise_aware' else 'shortcut_'+mode
    CONTROL_COMMANDS[name]=['python3','-m','redteam.hardening.solvers.probe','--mode',mode]
for name,command in CONTROL_COMMANDS.items():
    path=Path('methods')/('hardening_'+name)/'solver.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({'name':name,'command':command})+'\n')
