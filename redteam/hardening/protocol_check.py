"""Adversarial checks on both independent scorers; run in the joint job."""
import copy
import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

report = {}
for side in ('train', 'test'):
    spec = importlib.util.spec_from_file_location(f'check_{side}', f'eval/{side}/evaluate.py')
    e = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = e
    spec.loader.exec_module(e)
    poses = {'q_st': [[1., 0., 0., 0.]]*2, 'q_dual': [[0., 0., 0., 0.]]*2}
    good = {'estimates': {'0': poses}}
    truth = [('0', 2, [([1., 0., 0., 0.], [0., 0., 0.])]*2)]
    assert e.score_output(good, truth) == ([0.], [0.])
    cases = {}
    cases['one_pose'] = copy.deepcopy(good)
    cases['one_pose']['estimates']['0']['q_st'] = poses['q_st'][:1]
    cases['missing_id'] = {'estimates': {}}
    cases['extra_id'] = copy.deepcopy(good)
    cases['extra_id']['estimates']['extra'] = poses
    for label, value in [('nan', float('nan')), ('infinity', float('inf')),
                         ('overflow', 10**400), ('null', None), ('bool', True)]:
        cases[label] = copy.deepcopy(good)
        cases[label]['estimates']['0']['q_dual'][0] = [value, 0., 0., 0.]
    for label, field, value in [('nonunit', 'q_st', [2., 0., 0., 0.]),
                                ('nonorthogonal', 'q_dual', [1., 0., 0., 0.]),
                                ('huge_translation', 'q_dual', [0., 1e7, 0., 0.])]:
        cases[label] = copy.deepcopy(good)
        cases[label]['estimates']['0'][field][0] = value
    cases['truth_forgery'] = {**good, 'truth': {}}
    cases['baseline_forgery'] = {**good, 'baselines': {}}
    rejected = []
    for label, value in cases.items():
        try:
            e.score_output(value, truth)
        except e.InvalidOutput:
            rejected.append(label)
        else:
            raise AssertionError((side, label, 'was accepted'))
    for text in ('{"estimates":{},"estimates":{}}', '{"x":NaN}', '{"x":Infinity}'):
        try:
            e.strict_json(text)
        except e.InvalidOutput:
            pass
        else:
            raise AssertionError('non-strict JSON accepted')

    cfg = {'experiments': {'x': {'weight': 1., 'metrics': {
        'a': {'coefficient': -2., 'higher_is_better': False},
        'b': {'coefficient': 3., 'higher_is_better': True}}}}}
    anchor = {'x': {'a': 10., 'b': 10.}}
    values = {'better': {'x': {'a': 8., 'b': 12.}},
              'worse': {'x': {'a': 12., 'b': 8.}},
              'failed': {'x': {'a': 100., 'b': 0.}}}
    statuses = {n: {'status': 'failed' if n == 'failed' else 'ok'} for n in values}
    ranks, scales = e.normalized_ranks(values, statuses, anchor, cfg)
    assert ranks['better'] > 0 > ranks['worse'] > ranks['failed']
    mu = (10+8+12+100)/4
    assert abs(scales['x']['a']-math.sqrt(sum((v-mu)**2 for v in (10,8,12,100))/4)) < 1e-12
    scaled, scaled_anchor = copy.deepcopy(values), copy.deepcopy(anchor)
    for v in scaled.values():
        v['x']['a'] *= 1000
    scaled_anchor['x']['a'] *= 1000
    cfg['experiments']['x']['metrics']['a']['coefficient'] = 2.
    ranks2, _ = e.normalized_ranks(scaled, statuses, scaled_anchor, cfg)
    assert all(abs(ranks[n]-ranks2[n]) < 1e-12 for n in ranks)
    values['fixed_baseline'] = {'x': {'a': 1e100, 'b': -1e100}}
    statuses['fixed_baseline'] = {'status': 'ok', 'evaluator_owned': True}
    assert e.normalized_ranks(values, statuses, anchor, cfg)[0] == ranks

    # A global right pose gauge changes no scientific prediction. Verify
    # translation-origin invariance even with imperfect recovered rotations.
    sq = math.sqrt(.5)
    true = [([1.,0.,0.,0.], [0.,0.,0.]), ([sq,0.,0.,sq], [1.,0.,0.])]
    estimate = [([1.,0.,0.,0.], [.1,.2,0.]),
                ([math.cos(.7),0.,0.,math.sin(.7)], [.9,.1,.2])]
    shift = [40., -20., 5.]
    right_rotation = [math.cos(.2), math.sin(.2), 0., 0.]
    shifted = [(e.q_mul(q, right_rotation), [a+b for a,b in zip(t,e.rotate(q,shift))]) for q,t in estimate]
    original_errors, shifted_errors = e.aligned_errors(true, estimate), e.aligned_errors(true, shifted)
    assert max(abs(a-b) for a,b in zip(original_errors, shifted_errors)) < 1e-12

    # Exercise main(), including malformed/missing/reserved/duplicate manifests,
    # partial outputs and complete valid outputs that fail the recovery gate.
    # Tiny fixtures only; the full scientific suite is rescored separately.
    e.CACHE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='protocol_', dir=e.CACHE) as work:
        folder = Path(work)
        test_poses = {'q_st': [[1.,0.,0.,0.], [sq,0.,0.,sq]],
                      'q_dual': [[0.,0.,0.,0.], [0.,.5*sq,-.5*sq,0.]]}
        labelled = [(key, 2, [e.pose(a,b) for a,b in zip(test_poses['q_st'],test_poses['q_dual'])]) for key in ('0','1')]
        raw_good = json.dumps({'estimates': {key:test_poses for key in ('0','1')}})
        raw_bad_task = json.dumps({'estimates': {key:poses for key in ('0','1')}})
        manifests = []
        entries = [('good', {'name':'good','command':['dummy']}),
                   ('partial', {'name':'partial','command':['dummy']}),
                   ('task_failure', {'name':'task_failure','command':['dummy']}),
                   ('invalid_json', {'name':'invalid_json','command':['dummy']}),
                   ('reserved', {'name':'_reference','command':['dummy']}),
                   ('reserved_failure_id', {'name':'invalid_manifest_0123456789ab','command':['dummy']}),
                   ('duplicate_1', {'name':'dup','command':['dummy']}),
                   ('duplicate_2', {'name':'dup','command':['dummy']}),
                   ('invalid_command', {'name':'invalid','command':[]}),
                   ('invalid_object', [])]
        for label, value in entries:
            path = folder/(label+'.json')
            path.write_text(json.dumps(value))
            manifests.append(path)
        manifests.append(folder/'missing_primary.json')
        (folder/'ranking.json').write_text(json.dumps({'experiments': {'x': {'weight': 1., 'metrics': {
            k:{'coefficient':-1.,'higher_is_better':False} for k in e.METRICS}}}}))
        def run_solver(manifest, payload, directory):
            name = manifest['name']
            if name == 'partial':
                return json.dumps({'estimates': {'0':test_poses}})
            if name == 'task_failure':
                return raw_bad_task
            if name == 'invalid_json':
                return '{'
            return raw_good
        patches = {
            '__file__': str(folder/'evaluate.py'),
            'SETTINGS': {'x':(2,.5,.1,10.)}, 'TRIALS': {'x':2}, 'CACHE': folder/'cache',
            '_load_comparators': lambda:SimpleNamespace(reference=lambda:None, COMPARATORS={}),
            'discover_manifests': lambda:manifests,
            'build_experiment': lambda exp:({'instances': []}, labelled),
            'raw_comparator': lambda fn,payload:raw_good, 'run_solver':run_solver,
        }
        with patch.multiple(e, **patches), patch.object(sys,'argv',['check','--output',str(folder/'scores.json')]):
            e.main()
        scores = json.loads((folder/'scores.json').read_text())
        methods = scores['_metadata']['methods']
        results = scores['experiments']['x']['results']
        penalties = scores['_metadata']['failure_values']['x']
        assert methods['good']['status'] == 'ok'
        assert len(methods) == len(manifests)
        extra_penalties = {'x':penalties, 'other':dict(penalties)}
        assert e.finalized_metrics({'x':results['good']}, True, extra_penalties) == extra_penalties
        for name, value in methods.items():
            assert set(results[name]) == set(e.METRICS)
            assert all(math.isfinite(v) for v in results[name].values())
            if name != 'good':
                assert value['status'] == 'failed'
                assert results[name] == penalties
                assert value['rank'] < methods['good']['rank']
    report[side] = {'invalid_cases_rejected':rejected, 'strict_json':True,
                    'finite_failure_penalties_all_experiments':True,
                    'manifest_failures_have_complete_metrics':True,
                    'all_attempts_enter_population_scale':True,
                    'failed_rank_below_every_success':True,
                    'gauge_invariant':True, 'direction_sign_and_units_invariant':True}
Path('redteam/hardening/protocol_check.json').write_text(json.dumps(report,indent=2)+'\n')
