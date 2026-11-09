"""Compute-node diagnostics for the original, stored, and vectorized runs."""
from __future__ import annotations

from redteam.audit import CACHE, EXPERIMENTS, ROOT, RT, load_visible_metrics, read, write


def compare(left, right, metrics):
    pairs = list(zip(left['trials'], right['trials']))
    rows = []
    for a, b in pairs:
        ea = metrics.aligned_errors(a['truth'], a['estimate'])
        eb = metrics.aligned_errors(b['truth'], b['estimate'])
        rows.append({
            'seed': a['seed'],
            'pose_component_max_abs_difference': max(
                abs(x-y) for p, q in zip(a['estimate'], b['estimate'])
                for key in ('q_st', 'q_dual') for x, y in zip(p[key], q[key])),
            'aligned_error_difference': [x-y for x, y in zip(ea, eb)],
            'init_iters': [a['init_iters'], b['init_iters']],
        })
    return {
        'trial_counts': [len(left['trials']), len(right['trials'])],
        'truth_and_seeds_identical': all(a['truth'] == b['truth'] and a['seed'] == b['seed'] for a, b in pairs),
        'artifact_settings': [{key: obj.get(key) for key in ('n', 'p', 'sigma_t', 'sigma_r_deg', 'max_iter')}
                              for obj in (left, right)],
        'max_pose_component_difference': max(row['pose_component_max_abs_difference'] for row in rows),
        'max_aligned_error_difference': max(abs(x) for row in rows for x in row['aligned_error_difference']),
        'worst_trials': sorted(rows, key=lambda row: max(abs(x) for x in row['aligned_error_difference']), reverse=True)[:5],
    }


def main():
    metrics = load_visible_metrics()
    result = {}
    for exp in EXPERIMENTS:
        name = f'{exp}_dqgpm_results.json'
        original = read(CACHE / 'original_reference_seed0' / name)
        stored = read(ROOT / 'checkpoints' / name)
        for trial in stored['trials']:
            trial.pop('history', None)
        pilot = read(CACHE / 'reference_seed0' / name)
        result[exp] = {
            'stored_vs_unmodified': compare(stored, original, metrics),
            'vectorized_vs_unmodified': compare(pilot, original, metrics),
        }
    write(RT / 'reference_consistency.json', result)
    print('Reference consistency diagnostics saved.', flush=True)


if __name__ == '__main__':
    main()
