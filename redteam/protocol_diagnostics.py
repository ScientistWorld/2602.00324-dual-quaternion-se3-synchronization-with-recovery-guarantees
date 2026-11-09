"""Compute-node checks of paper aggregation and stale reference artifacts."""
from __future__ import annotations

from redteam.audit import CACHE, EXPERIMENTS, ROOT, RT, load_visible_metrics, read, write


def statistics(trials, metrics):
    errors = [metrics.aligned_errors(t['truth'], t['estimate']) for t in trials]
    result = {}
    for column, label in enumerate(('error_R', 'error_T')):
        values = sorted(e[column] for e in errors)
        # Interpret the paper's 15% trimmed mean as dropping 15% per tail.
        cut = int(.15 * len(values))
        result[label] = {
            'mean': metrics.mean(values),
            'std': metrics.std(values),
            'trim15_each_tail_mean': metrics.mean(values[cut:-cut]),
        }
    return result


def main():
    from method.sync import build_synthetic_measurement

    metrics = load_visible_metrics()
    result = {}
    for exp in EXPERIMENTS:
        filename = f'{exp}_dqgpm_results.json'
        stored = read(ROOT / 'checkpoints' / filename)
        original = read(CACHE / 'original_reference_seed0' / filename)
        baseline = read(CACHE / 'original_reference_seed0' / f'{exp}_dq_spectral_results.json')
        diagnostics = []
        for a, b in zip(stored['trials'], original['trials'], strict=True):
            c, _, _ = build_synthetic_measurement(b['n'], b['p'], b['sigma_t'], b['sigma_r_deg'], b['seed'])
            isolated = [i for i, neighbors in enumerate(c.neighbors) if len(neighbors) == 1]
            changed = [i for i, (p, q) in enumerate(zip(a['estimate'], b['estimate'], strict=True))
                       if max(abs(x-y) for key in ('q_st', 'q_dual') for x, y in zip(p[key], q[key], strict=True)) > 1e-6]
            spectral_changed = [i for i, (p, q) in enumerate(zip(a['spectral_estimate'], b['spectral_estimate'], strict=True))
                                if max(abs(x-y) for key in ('q_st', 'q_dual') for x, y in zip(p[key], q[key], strict=True)) > 1e-6]
            if changed or isolated or spectral_changed:
                diagnostics.append({'seed': b['seed'], 'isolated_nodes': isolated,
                                    'changed_estimate_nodes': changed,
                                    'changed_spectral_nodes': spectral_changed})
        test_count = sum(t['seed'] % 7 >= 3 for t in original['trials'])
        result[exp] = {
            'test_trial_count': test_count,
            'full_original_100_trials': statistics(original['trials'], metrics),
            'full_fixed_spectral_100_trials': statistics(baseline['trials'], metrics),
            'full_stored_100_trials': statistics(stored['trials'], metrics),
            'stored_original_node_changes': diagnostics,
            'all_changed_nodes_are_isolated': all(set(row['changed_estimate_nodes']) <= set(row['isolated_nodes'])
                                                 for row in diagnostics),
            'all_spectral_changed_nodes_are_isolated': all(set(row['changed_spectral_nodes']) <= set(row['isolated_nodes'])
                                                          for row in diagnostics),
        }
    write(RT / 'protocol_diagnostics.json', result)
    print('Paper-protocol and artifact diagnostics saved.', flush=True)


if __name__ == '__main__':
    main()
