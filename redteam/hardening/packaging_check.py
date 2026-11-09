"""Check canonical artifacts and record the verified scope, without inference."""
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def main():
    audit = read('redteam/hardening/report.json')
    reference = read('scoring/reference.json')
    expected = {'dqgpm', 'dq_spectral', 'matrix_eig'}
    result = {
        'status': 'verified_with_unresolved_comparison',
        'all_requested_conditions_met': audit['all_requested_conditions_met'],
        'unresolved_requirements': audit['unresolved_requirements'],
        'slices': {},
    }
    for side in ('train', 'test'):
        scores = read(f'scoring/scores_{side}.json')
        meta = scores['_metadata']
        assert set(meta['methods']) == expected
        assert not meta['rejected_manifests']
        assert all(v['status'] == 'ok' for v in meta['methods'].values())
        assert meta['methods']['dqgpm']['rank'] == 0.
        assert meta['methods']['dqgpm']['evaluator_owned'] is False
        assert all(meta['methods'][n]['evaluator_owned'] for n in expected-{'dqgpm'})
        assert set(scores['experiments']) == set(reference['experiments'])
        for exp, spec in scores['experiments'].items():
            assert set(spec['results']) == expected
            assert spec['results']['dqgpm'] == meta['reference'][exp]
            for name in expected:
                # Canonical scores use the exact raw-output audit runs.
                assert spec['results'][name] == audit['after'][side]['metrics'][name][exp]
                if side == 'train':
                    numeric = {k:v for k,v in reference['experiments'][exp]['results'][name].items() if k != 'type'}
                    assert spec['results'][name] == numeric
            for key in reference['experiments'][exp]['metrics']:
                assert len({spec['results'][n][key] for n in expected}) > 1, (side, exp, key)
            # Honest train and test means remain on comparable scales.
            development = audit['after']['train']['metrics']['dqgpm'][exp]
            hidden = audit['after']['test']['metrics']['dqgpm'][exp]
            for key in ('error_R', 'error_T'):
                assert abs(hidden[key]/development[key]-1.) < .10
                assert hidden[key] > audit['after']['test']['metrics']['better_noise_aware'][exp][key]
                assert hidden[key] < audit['after']['test']['metrics']['weaker_spectral'][exp][key]
        result['slices'][side] = {'canonical_methods': sorted(expected),
                                  'all_valid': True, 'reference_rank': 0.,
                                  'metrics_match_final_raw_audit': True}
    assert read('scoring/scores.json') == read('scoring/scores_train.json')
    # Preserve both the positive refinement/headroom result and the negative
    # external comparison. A valid package is not proof of the whole paper.
    Path('redteam/hardening/packaging_check.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
