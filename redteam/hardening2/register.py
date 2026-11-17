"""Register the audit cohort as methods/hardening_*/solver.json (gitignored)."""
import json
import shutil
from pathlib import Path

PROBE = ['python3', '-m', 'redteam.hardening2.probe', '--mode']
OLD = ['python3', '-m', 'redteam.hardening.solvers.probe', '--mode']
CONTROLS = {
    'reference_seed1': ['python3', '-m', 'method.solve', '--seed', '1'],
    'reference_seed2': ['python3', '-m', 'method.solve', '--seed', '2'],
    'weaker_spectral': ['python3', '-m', 'method.solve', '--stage', 'spectral'],
    'better_mle_refinement': PROBE + ['better'],
    'shortcut_pool_trials': PROBE + ['pool'],
    'shortcut_public_truth': PROBE + ['public_truth'],
    'shortcut_zero_translation': PROBE + ['zero_translation'],
    'shortcut_isolated_identity': PROBE + ['isolated_identity'],
    # previously repaired shortcuts, replayed against the new experiments
    'shortcut_rebuild_answers': OLD + ['rebuild_answers'],
    'shortcut_one_pose': OLD + ['one_pose'],
    'shortcut_select_trials': OLD + ['select_trials'],
    'shortcut_nan': OLD + ['nan'],
}

for path in Path('methods').glob('hardening_*'):
    shutil.rmtree(path)
for name, command in CONTROLS.items():
    path = Path('methods') / ('hardening_' + name) / 'solver.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'name': name, 'command': command}) + '\n')
print('registered', sorted(CONTROLS))
