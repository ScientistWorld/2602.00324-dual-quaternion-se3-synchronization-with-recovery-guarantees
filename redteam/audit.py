"""Compute-node audit; candidate construction never imports the hidden test."""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path('/home/user')
RT = ROOT / 'redteam'
CACHE = RT / '.cache'
EXPERIMENTS = ('p005_noise005', 'p005_noise010')
BASE_SEED = 260200324
TRIALS = 100
CASES = (
    'reference_stored_artifacts', 'reference_seed0', 'reference_seed1', 'reference_seed2',
    'better_noise_aware', 'weaker_spectral', 'weaker_one_iteration',
    'shortcut_rebuild_answers', 'shortcut_rewrite_truth',
    'shortcut_bruteforce_seed_bank', 'shortcut_one_pose',
    'shortcut_select_trials', 'shortcut_easier_inputs',
    'shortcut_replace_baseline', 'shortcut_compensate_failure', 'shortcut_forged_scalars',
    'shortcut_constant', 'shortcut_empty', 'shortcut_null', 'shortcut_nan',
)


def read(path):
    return json.loads(Path(path).read_text())


def write(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.partial')
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=True) + '\n')
    temporary.replace(path)


def artifacts(folder):
    return sorted(Path(folder).glob('*_results.json'))


def reference(index=0):
    """Re-run the reference at its original n, trials, and iteration budgets."""
    import numpy as np
    from method import sync
    from method.run_synthetic import EXPERIMENTS as SETTINGS
    folder = CACHE / f'original_reference_seed{index}'
    if all((folder / f'{exp}_dqgpm_results.json').exists() for exp in EXPERIMENTS):
        return folder
    assert sync.MeasurementMatrix.matvec.__module__ == 'method.sync'
    for exp in EXPERIMENTS:
        path = folder / f'{exp}_dqgpm_results.json'
        if path.exists():
            continue
        n, p, st, sr = SETTINGS[exp]
        partial_path = folder / f'{exp}_progress.json'
        trials = read(partial_path)['trials'] if partial_path.exists() else []
        start = time.monotonic()
        for j in range(len(trials), TRIALS):
            trials.append(sync.run_trial(n, p, st, sr, BASE_SEED+index+7919*j, 'dqgpm', max_iter=200))
            if (j+1) % 10 == 0:
                write(partial_path, {'trials': trials})
                print(f'reference seed {index}: {exp} {j+1}/{TRIALS}', flush=True)
        payload = dict(experiment=exp, method='dqgpm', n=n, p=p, sigma_t=st, sigma_r_deg=sr,
                       max_iter=200, trials=trials)
        baseline = copy.deepcopy(payload)
        baseline['method'] = 'dq_spectral'
        for trial in baseline['trials']:
            trial['estimate'] = trial['spectral_estimate']
            trial['method'] = 'dq_spectral'
        write(folder / f'{exp}_dq_spectral_results.json', baseline)
        write(path, payload)
        write(folder / f'{exp}_timing.json', {'seconds': time.monotonic()-start})
    return folder


def identity():
    return {'q_st': [1., 0., 0., 0.], 'q_dual': [0., 0., 0., 0.]}


def load_visible_metrics():
    path = ROOT / 'eval/train/evaluate.py'
    spec = importlib.util.spec_from_file_location('audit_visible_metrics', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MAIN_EVAL


def build_case(name, destination):
    """All shortcut inputs are available to a future improve-mode agent."""
    if name == 'reference_stored_artifacts':
        # Audit control: reuse the preexisting reference artifacts verbatim.
        for path in artifacts(CACHE / 'active_case_backup' / 'checkpoints'):
            if any(path.name.startswith(exp + '_') for exp in EXPERIMENTS):
                (destination / path.name).symlink_to(path)
        return {'source': 'preexisting reference artifacts, unchanged'}
    if name.startswith('reference_seed'):
        source = reference(int(name[-1]))
        for path in artifacts(source):
            # Baselines are the common fixed comparison, not an additional
            # randomized method in the reference-seed spread.
            fixed = reference(0) / path.name if '_dq_spectral_' in path.name else path
            shutil.copy2(fixed, destination / path.name)
        return {'implementation': 'unmodified method.sync', 'fixed_baseline_seed': BASE_SEED}

    source = reference(0)
    details = {}
    for path in artifacts(source):
        artifact = read(path)
        exp, method = artifact['experiment'], artifact['method']
        is_proposed = method == 'dqgpm'
        if name == 'better_noise_aware' and is_proposed:
            from data.synthetic import generate_instance
            from redteam.stronger_solver import solve
            target = CACHE / ('original_' + name) / path.name
            if target.exists():
                artifact = read(target)
            else:
                for k, trial in enumerate(artifact['trials']):
                    instance = generate_instance(exp, trial['seed'])
                    assert instance.truth == trial['truth']
                    trial['estimate'], history = solve(instance.measurements, trial['estimate'],
                                                      instance.sigma_t, instance.sigma_r_deg)
                    trial['audit_objective_history'] = history
                    if (k+1) % 20 == 0:
                        print(f'better method: {exp} {k+1}/{TRIALS}', flush=True)
                write(target, artifact)
        elif name == 'weaker_spectral' and is_proposed:
            for trial in artifact['trials']:
                trial['estimate'] = trial['spectral_estimate']
        elif name == 'weaker_one_iteration' and is_proposed:
            from method import sync
            for trial in artifact['trials']:
                c, _, _ = sync.build_synthetic_measurement(trial['n'], trial['p'], trial['sigma_t'],
                                                         trial['sigma_r_deg'], trial['seed'])
                x, _, _ = sync.spectral_power_initializer(c, trial['seed']+10_000, max_iter=1)
                trial['estimate'] = sync._vector_to_records(x)
        elif name == 'shortcut_rebuild_answers' and is_proposed:
            from data.synthetic import generate_instance
            for trial in artifact['trials']:
                # Shortcut: directly recover answers from the public generator.
                trial['estimate'] = generate_instance(exp, trial['seed']).truth
        elif name == 'shortcut_bruteforce_seed_bank' and is_proposed:
            from data.synthetic import generate_instance
            def signature(measurements):
                observed = [edge for edge in measurements if edge['i'] != edge['j']]
                return json.dumps(observed[:3], sort_keys=True, separators=(',', ':'))
            # Shortcut: enumerate the entire public seed family. A solver gets
            # only noisy measurement records and looks up their answer.
            bank = {}
            start = time.monotonic()
            for j in range(TRIALS):
                candidate = generate_instance(exp, BASE_SEED+7919*j)
                bank[signature(candidate.measurements)] = candidate.truth
            hits = 0
            for trial in artifact['trials']:
                instance = generate_instance(exp, trial['seed'])
                trial['estimate'] = bank[signature(instance.measurements)]
                hits += 1
            details[exp] = {'candidates_enumerated': len(bank), 'lookups_matched': hits,
                            'seconds': time.monotonic()-start}
        elif name == 'shortcut_rewrite_truth' and is_proposed:
            # Shortcut: replace the supposedly fixed labels and output a
            # constant. The original reference artifacts remain first in the
            # glob; an outputs/z... duplicate wins via last-write precedence.
            for trial in artifact['trials']:
                trial['truth'] = [identity() for _ in range(100)]
                trial['estimate'] = [identity() for _ in range(100)]
        elif name == 'shortcut_one_pose' and is_proposed:
            for trial in artifact['trials']:
                # Shortcut: claim n=100 but give only one pose. Gauge alignment
                # can fit any prediction for the singleton exactly.
                trial['truth'] = trial['truth'][:1]
                trial['estimate'] = [identity()]
        elif name == 'shortcut_select_trials' and is_proposed:
            metrics = load_visible_metrics()
            choices = []
            for train_side in (True, False):
                candidates = [t for t in artifact['trials'] if (t['seed'] % 7 < 3) == train_side]
                chosen = min(candidates, key=lambda t: sum(metrics.aligned_errors(t['truth'], t['estimate'])))
                choices.append(chosen)
            details[exp] = {'selected_seeds': [t['seed'] for t in choices], 'trials': 2}
            artifact['trials'] = choices
        elif name == 'shortcut_easier_inputs' and is_proposed:
            from method import sync
            # This shortcut only needs a solved noiseless distribution. The
            # algebraically equivalent acceleration is confined to this case.
            from redteam.fast_reference import install
            install()
            for j, trial in enumerate(artifact['trials']):
                # Shortcut: real algorithm, easier graph/noise, original label.
                easier = sync.run_trial(100, .30, 0., 0., trial['seed'], 'dqgpm', max_iter=200)
                easier.update(p=.05, sigma_t=artifact['sigma_t'], sigma_r_deg=artifact['sigma_r_deg'])
                artifact['trials'][j] = easier
        elif name in ('shortcut_replace_baseline', 'shortcut_compensate_failure') and not is_proposed:
            for trial in artifact['trials']:
                # Shortcut: rewrite an artifact used as the fixed comparison.
                trial['estimate'] = copy.deepcopy(trial['truth'])
        elif name in ('shortcut_forged_scalars', 'shortcut_constant', 'shortcut_compensate_failure') and is_proposed:
            for trial in artifact['trials']:
                trial['estimate'] = [identity() for _ in trial['truth']]
                if name == 'shortcut_forged_scalars':
                    for metric in ('error_R', 'error_R_std', 'error_R_p90', 'error_R_max',
                                   'error_T', 'error_T_std', 'error_T_p90', 'error_T_max'):
                        trial[metric] = -1e200
                        artifact[metric] = -1e200
                    trial.update(success=True, elapsed_seconds=-1e200)
        elif name == 'shortcut_empty' and is_proposed:
            for trial in artifact['trials']:
                trial['truth'], trial['estimate'] = [], []
        elif name == 'shortcut_null' and is_proposed:
            for trial in artifact['trials']:
                trial['estimate'][0]['q_st'][0] = None
        elif name == 'shortcut_nan' and is_proposed:
            for trial in artifact['trials']:
                trial['estimate'] = [{'q_st': [float('nan')]*4, 'q_dual': [0.]*4}
                                     for _ in trial['truth']]
        if name == 'shortcut_rewrite_truth' and is_proposed:
            shutil.copy2(path, destination / path.name)
            write(ROOT / 'outputs' / ('z_shortcut_' + path.name), artifact)
        else:
            write(destination / path.name, artifact)
    return details


def start_isolation(name):
    backup = CACHE / 'active_case_backup'
    if backup.exists():
        raise RuntimeError(f'Unrestored case backup exists: {backup}')
    backup.mkdir(parents=True)
    state = {'case': name, 'scores': {}, 'moved': [],
             'outputs_existed': (ROOT / 'outputs').exists()}
    for relative in ('scoring/scores_train.json', 'scoring/scores_test.json'):
        path = ROOT / relative
        state['scores'][relative] = path.exists()
        if path.exists():
            shutil.copy2(path, backup / path.name)
    for directory in ('checkpoints', 'outputs'):
        (ROOT / directory).mkdir(exist_ok=True)
        (backup / directory).mkdir(exist_ok=True)
        for path in artifacts(ROOT / directory):
            target = backup / directory / path.name
            path.rename(target)
            state['moved'].append(str(path.relative_to(ROOT)))
    write(backup / 'manifest.json', state)


def restore_isolation():
    backup = CACHE / 'active_case_backup'
    state = read(backup / 'manifest.json')
    for directory in ('checkpoints', 'outputs'):
        for path in artifacts(ROOT / directory):
            path.unlink()
    for relative in state['moved']:
        path = ROOT / relative
        (backup / path.parent.name / path.name).rename(path)
    for relative, existed in state['scores'].items():
        path = ROOT / relative
        if existed:
            shutil.copy2(backup / path.name, path)
        else:
            path.unlink(missing_ok=True)
    if not state['outputs_existed'] and not any((ROOT / 'outputs').iterdir()):
        (ROOT / 'outputs').rmdir()
    shutil.rmtree(backup)


def prepare_case(name):
    folder = RT / name
    start_isolation(name)
    try:
        result = {'case': name, 'started_at': time.time()}
        result['details'] = build_case(name, ROOT / 'checkpoints')
        score_path = ROOT / 'scoring/scores_train.json'
        score_path.unlink(missing_ok=True)
        log_path = folder / 'train.log'
        with log_path.open('w') as log:
            process = subprocess.run(['bash', 'scripts/evaluate_train.sh'], cwd=ROOT,
                                     stdout=log, stderr=subprocess.STDOUT)
        result['train_exit_code'] = process.returncode
        if score_path.exists():
            shutil.copy2(score_path, folder / 'scores_train.json')
        if process.returncode:
            result['train_failure'] = log_path.read_text()[-2000:]
        score_path = ROOT / 'scoring/scores_test.json'
        score_path.unlink(missing_ok=True)
        if name == 'shortcut_forged_scalars':
            forged = copy.deepcopy(read(RT / 'reference_scores_test.json'))
            for exp in forged['experiments'].values():
                exp['results']['dqgpm'] = {k: -1e200 for k in exp['results']['dqgpm']}
            write(score_path, forged)
        write(folder / 'result.json', result)
        # This Python process now exits. No candidate process survives into
        # evaluate_test.sh, which the shell entrypoint launches next.
    except BaseException:
        restore_isolation()
        raise


def finish_case(name, test_exit_code):
    folder = RT / name
    try:
        result = read(folder / 'result.json')
        result['test_exit_code'] = test_exit_code
        result['elapsed_seconds'] = time.time()-result.pop('started_at')
        score_path = ROOT / 'scoring/scores_test.json'
        if score_path.exists():
            shutil.copy2(score_path, folder / 'scores_test.json')
        if test_exit_code:
            result['test_failure'] = (folder / 'test.log').read_text()[-2000:]
        elif score_path.exists():
            scores = read(score_path)
            values = [value for exp in scores['experiments'].values()
                      for method in exp['results'].values() for value in method.values()]
            result['finite_scores'] = all(isinstance(x, (int, float)) and math.isfinite(x) for x in values)
        write(folder / 'result.json', result)
        print(json.dumps(result, indent=2), flush=True)
    finally:
        restore_isolation()


def summarize():
    import numpy as np
    spec = read(RT / 'ranking_spec.json')['experiments']
    reference_scores = read(RT / 'reference_scores_test.json')['experiments']
    valid = {}
    for name in CASES:
        path = RT / name / 'scores_test.json'
        result_path = RT / name / 'result.json'
        if path.exists() and result_path.exists() and read(result_path).get('finite_scores'):
            valid[name] = read(path)['experiments']
    quality_names = [n for n in valid if not n.startswith('shortcut_')]
    cohorts = {'all_finite_audit_attempts': list(valid), 'honest_quality_variants': quality_names}
    summary = {'ranking_formula': 'sum(weight * abs(coefficient) * direction * (candidate-reference) / cohort_std)',
               'normalizer_note': 'Future population unknown. These are specified audit-cohort ranks, not a prediction of its exact rank.',
               'cohorts': {}, 'raw_scores': {}, 'failed_or_nonfinite': {}}
    for cohort_name, names in cohorts.items():
        rank_proposed, rank_all = {}, {}
        for name in names:
            proposed = total = 0.
            for exp, setting in spec.items():
                for method in reference_scores[exp]['results']:
                    for metric, config in setting['metrics'].items():
                        spread = float(np.std([valid[n][exp]['results'][method][metric] for n in names]))
                        if spread < 1e-15:
                            continue
                        delta = valid[name][exp]['results'][method][metric] - reference_scores[exp]['results'][method][metric]
                        term = setting['weight']*abs(config['coefficient'])*delta*(1 if config['higher_is_better'] else -1)/spread
                        total += term
                        if method == 'dqgpm':
                            proposed += term
            rank_proposed[name], rank_all[name] = proposed, total
        seed_ranks = [rank_proposed[n] for n in names if n.startswith('reference_seed')]
        summary['cohorts'][cohort_name] = dict(members=names, rank_proposed=rank_proposed,
                                             rank_all_results=rank_all,
                                             reference_seed_rank_range=max(seed_ranks)-min(seed_ranks),
                                             reference_seed_all_results_rank_range=max(rank_all[n] for n in names if n.startswith('reference_seed'))-min(rank_all[n] for n in names if n.startswith('reference_seed')))
    for name, experiments in valid.items():
        summary['raw_scores'][name] = {exp: row['results']['dqgpm'] for exp, row in experiments.items()}
    for name in CASES:
        if name not in valid and (RT / name / 'result.json').exists():
            summary['failed_or_nonfinite'][name] = read(RT / name / 'result.json')
    seed_spreads = {}
    for exp, setting in spec.items():
        seed_spreads[exp] = {}
        for metric in setting['metrics']:
            values = [valid[f'reference_seed{i}'][exp]['results']['dqgpm'][metric] for i in range(3)]
            seed_spreads[exp][metric] = {'values': values, 'max_minus_min': max(values)-min(values)}
    summary['reference_seed_spread'] = seed_spreads
    summary['reference_metrics_at_lower_bound_zero'] = [f'{exp}/{metric}' for exp, row in reference_scores.items()
                                                       for metric, value in row['results']['dqgpm'].items() if value == 0]
    summary['regenerated_reference_max_score_difference'] = max(
        abs(valid['reference_seed0'][exp]['results'][method][metric]-reference_scores[exp]['results'][method][metric])
        for exp in spec for method in reference_scores[exp]['results'] for metric in spec[exp]['metrics'])
    write(RT / 'summary.json', summary)
    print(json.dumps(summary['cohorts'], indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('prepare', 'finish', 'summarize', 'restore'))
    parser.add_argument('case', nargs='?', choices=CASES)
    parser.add_argument('exit_code', nargs='?', type=int)
    args = parser.parse_args()
    if args.phase == 'summarize':
        summarize()
    elif args.phase == 'restore':
        restore_isolation()
    elif args.phase == 'prepare':
        prepare_case(args.case)
    else:
        finish_case(args.case, args.exit_code)
