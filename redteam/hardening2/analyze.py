"""Summarize the joint audit: ranks, paired uncertainty, headroom, shortcuts.

Reads the all-candidate score files and the per-trial errors that each
evaluator keeps in its own cache. Writes redteam/hardening2/report.json.
Nothing here feeds back into scoring.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

PAIRED = ('better_mle_refinement', 'weaker_spectral', 'reference_seed1', 'reference_seed2',
          'dq_spectral', 'matrix_eig', 'sdr', 'shortcut_pool_trials', 'shortcut_isolated_identity')
BOOT = ('better_mle_refinement', 'weaker_spectral', 'reference_seed1', 'reference_seed2', 'matrix_eig',
        'dq_spectral', 'shortcut_pool_trials', 'shortcut_isolated_identity')


def read(path):
    return json.loads(Path(path).read_text())


def summaries(x):
    return {'': x.mean(axis=-1), '_std': x.std(axis=-1), '_p90': np.quantile(x, .9, axis=-1), '_max': x.max(axis=-1)}


def main():
    rng = np.random.default_rng(20261117)
    report = {'ranks': {}, 'comparator_as_if_ranks': {}, 'per_experiment_rank': {}, 'paired': {}, 'paired_rank': {},
              'seed_rank_range': {}, 'reference_means': {}, 'scan_config_means': {}, 'statuses': {}}
    for side in ('train', 'test'):
        scores = read(f'redteam/hardening2/scores_{side}_all.json')
        details = read(f'eval/{side}/.cache/details.json')
        meta = scores['_metadata']
        cfg = read(f'eval/{side}/ranking.json')['experiments']
        scales = meta['rank_scales']
        anchor = meta['reference']
        report['statuses'][side] = {n: {'status': v['status'], 'rank': v.get('rank'), 'reason': v.get('reason')}
                                    for n, v in meta['methods'].items()}
        report['ranks'][side] = {n: v.get('rank') for n, v in meta['methods'].items() if not v['evaluator_owned']}
        report['reference_means'][side] = {e: {k: anchor[e][k] for k in ('error_R', 'error_T')} for e in anchor}
        report['scan_config_means'][side] = meta.get('scan_config_means', {})
        # Rank contribution of every method per experiment, with the cohort scales.
        per = {}
        for name, entry in meta['methods'].items():
            per[name] = {}
            for exp, spec in cfg.items():
                values = scores['experiments'][exp]['results'].get(name)
                if not values:
                    continue
                total = 0.0
                for key, definition in spec['metrics'].items():
                    sd = scales[exp][key]
                    if sd:
                        direction = 1.0 if definition['higher_is_better'] else -1.0
                        total += spec['weight']*abs(definition['coefficient'])*direction*(values[key]-anchor[exp][key])/sd
                per[name][exp] = total
        report['per_experiment_rank'][side] = per
        report['comparator_as_if_ranks'][side] = {n: {'rank': sum(per[n].values()), 'experiments': sorted(per[n])}
                                                  for n, v in meta['methods'].items() if v['evaluator_owned']}
        ok = {n for n, v in meta['methods'].items() if v['status'] == 'ok'}
        report['paired'][side] = {}
        for name in PAIRED:
            if name not in ok or name not in details:
                continue
            report['paired'][side][name] = {}
            for exp in details[name]:
                report['paired'][side][name][exp] = {}
                for key in ('error_R', 'error_T'):
                    delta = np.asarray(details['_reference'][exp][key]) - np.asarray(details[name][exp][key])
                    idx = rng.integers(0, len(delta), size=(1000, len(delta)))
                    ci = np.quantile(delta[idx].mean(axis=1), [.025, .975])
                    report['paired'][side][name][exp][key] = {
                        'mean_improvement': float(delta.mean()),
                        'relative_improvement': float(delta.mean()/np.mean(details['_reference'][exp][key])),
                        'paired_95_percent_interval': ci.tolist()}
        boot = {n: np.zeros(500) for n in BOOT if n in ok and n in details}
        for exp, spec in cfg.items():
            length = len(details['_reference'][exp]['error_R'])
            idx = rng.integers(0, length, size=(500, length))
            for key in ('error_R', 'error_T'):
                base = summaries(np.asarray(details['_reference'][exp][key])[idx])
                for name in boot:
                    if exp not in details[name]:
                        continue
                    vals = summaries(np.asarray(details[name][exp][key])[idx])
                    for suffix in base:
                        metric = key + suffix
                        sd = scales[exp][metric]
                        if sd:
                            definition = spec['metrics'][metric]
                            direction = 1.0 if definition['higher_is_better'] else -1.0
                            boot[name] += spec['weight']*abs(definition['coefficient'])*direction*(vals[suffix]-base[suffix])/sd
        report['paired_rank'][side] = {n: {'point': sum(per[n].values()) if n in per else None,
                                           'paired_95_percent_interval': np.quantile(v, [.025, .975]).tolist()}
                                       for n, v in boot.items()}
        seeds = [0.0] + [report['ranks'][side].get(n) for n in ('reference_seed1', 'reference_seed2')
                         if report['ranks'][side].get(n) is not None]
        report['seed_rank_range'][side] = max(seeds) - min(seeds)
    test = report['statuses']['test']
    rank = report['ranks']['test']
    report['checks'] = {
        'reference_at_zero_bound': [f'{e}/{k}' for e, v in read('redteam/hardening2/scores_test_all.json')['_metadata']['reference'].items()
                                    for k, x in v.items() if x <= 1e-12],
        'better_status': test.get('better_mle_refinement', {}).get('status'),
        'better_rank': rank.get('better_mle_refinement'),
        'better_exceeds_seed_range': (rank.get('better_mle_refinement') or -1) > report['seed_rank_range']['test'],
        'weaker_rank': rank.get('weaker_spectral'),
        'weaker_below_minus_seed_range': (rank.get('weaker_spectral') or 0) < -report['seed_rank_range']['test'],
        'shortcuts': {n: test[n] for n in test if n.startswith('shortcut_')},
        'train_test_reference_ratio': {e: {k: report['reference_means']['test'][e][k]/report['reference_means']['train'][e][k]
                                           for k in ('error_R', 'error_T')} for e in report['reference_means']['test']},
    }
    before = Path('redteam/hardening2/diag_before.json')
    if before.is_file():
        report['before_fix_diagnostics'] = read(before)
    Path('redteam/hardening2/report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'ranks': report['ranks'], 'comparators': report['comparator_as_if_ranks'],
                      'seed_range': report['seed_rank_range'], 'checks': report['checks'],
                      'paired_rank_test': report['paired_rank']['test']}, indent=1))


if __name__ == '__main__':
    main()
