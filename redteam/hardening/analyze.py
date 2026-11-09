"""Summarize audit scores and paired uncertainty; run only on the compute job.
Per-instance errors remain in the corresponding eval slice cache.
"""
import json
from pathlib import Path
import numpy as np


def read(path):return json.loads(Path(path).read_text())

def write(path,x):Path(path).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')


def main():
    before=read('redteam/summary.json')['cohorts']['all_finite_audit_attempts']['rank_all_results']
    report={'before_ranks':before,'after':{},'paired':{},'limitations':[
        'Finite synthetic instances cannot rule out general-purpose numerical optimization, which is an honest alternative.',
        'Worst-case and percentile metrics retain finite-sample uncertainty; paired bootstrap intervals are reported.',
        'This gym does not cover SDR, real scans, time complexity, or the theoretical recovery guarantee.']}
    rng=np.random.default_rng(20261109)
    for side in ('train','test'):
        scores=read(f'redteam/hardening/scores_{side}_all.json')
        details=read(f'eval/{side}/.cache/details.json')
        report['after'][side]={'methods':scores['_metadata']['methods'],'rejected_manifests':scores['_metadata']['rejected_manifests'],
                               'metrics':{n:{e:v['results'].get(n,{}) for e,v in scores['experiments'].items()} for n in scores['_metadata']['methods']}}
        # Common-input paired mean improvements (positive is better).
        report['paired'][side]={}
        for name in ('better_noise_aware','weaker_spectral','baseline_matrix_eig','reference_seed1','reference_seed2'):
            if scores['_metadata']['methods'].get(name,{}).get('status')!='ok':continue
            report['paired'][side][name]={}
            for exp in scores['experiments']:
                report['paired'][side][name][exp]={}
                for key in ('error_R','error_T'):
                    ref=np.asarray(details['_reference'][exp][key]);cand=np.asarray(details[name][exp][key])
                    delta=ref-cand
                    indices=rng.integers(0,len(delta),size=(1000,len(delta)))
                    ci=np.quantile(delta[indices].mean(axis=1),[.025,.975])
                    report['paired'][side][name][exp][key]={'mean_improvement':float(delta.mean()),'paired_95_percent_interval':ci.tolist()}
        # Bootstrap the complete weighted rank, retaining the same per-metric
        # scale as the audit cohort and resampling each common instance pair.
        cfg=read(f'eval/{side}/ranking.json')['experiments']
        scales=scores['_metadata']['rank_scales']
        boot={name:np.zeros(500) for name in ('better_noise_aware','weaker_spectral','baseline_matrix_eig','reference_seed1','reference_seed2') if name in report['paired'][side]}
        def summaries(x):
            return {'':x.mean(axis=1),'_std':x.std(axis=1),'_p90':np.quantile(x,.9,axis=1),'_max':x.max(axis=1)}
        for exp,spec in cfg.items():
            length=len(details['_reference'][exp]['error_R'])
            indices=rng.integers(0,length,size=(500,length))
            for key in ('error_R','error_T'):
                anchor=summaries(np.asarray(details['_reference'][exp][key])[indices])
                for name in boot:
                    vals=summaries(np.asarray(details[name][exp][key])[indices])
                    for suffix in anchor:
                        metric=key+suffix;sd=scales[exp][metric]
                        if sd:
                            definition=spec['metrics'][metric]
                            direction=1. if definition['higher_is_better'] else -1.
                            boot[name]+=spec['weight']*abs(definition['coefficient'])*direction*(vals[suffix]-anchor[suffix])/sd
        report.setdefault('paired_rank',{})[side]={name:{'rank':scores['_metadata']['methods'][name]['rank'],
            'paired_95_percent_interval':np.quantile(values,[.025,.975]).tolist()} for name,values in boot.items()}
        values=[scores['_metadata']['methods'][n]['rank'] for n in ('reference_seed1','reference_seed2') if n in boot]
        values.append(scores['_metadata']['methods']['dqgpm']['rank'] or 0.)
        report.setdefault('reference_seed_rank_range',{})[side]=max(values)-min(values)
    test=report['after']['test']['methods'];paired=report['paired_rank']['test']
    report['headroom_check']={
        'seed_controls_pass':all(test.get(n,{}).get('status')=='ok' for n in ('reference_seed1','reference_seed2')),
        'stronger_passes':test.get('better_noise_aware',{}).get('status')=='ok',
        'stronger_rank_positive':paired.get('better_noise_aware',{}).get('paired_95_percent_interval',[-1])[0]>0,
        'matrix_baseline_rank_negative':paired.get('baseline_matrix_eig',{}).get('paired_95_percent_interval',[1,1])[1]<0,
        'spectral_rank_negative':paired.get('weaker_spectral',{}).get('paired_95_percent_interval',[1,1])[1]<0,
        'stronger_exceeds_seed_range':(test.get('better_noise_aware',{}).get('rank') or 0.)>report['reference_seed_rank_range']['test'],
        'reference_at_zero_bounds':[f'{e}/{k}' for e,v in report['after']['test']['metrics']['dqgpm'].items() for k,x in v.items() if x<=1e-12],
    }
    write('redteam/hardening/report.json',report)
    # These assertions run AFTER the report is saved for useful failure diagnosis.
    assert all(report['headroom_check'][k] for k in ('seed_controls_pass','stronger_passes','stronger_rank_positive','matrix_baseline_rank_negative','spectral_rank_negative','stronger_exceeds_seed_range')),report['headroom_check']
    for name,entry in test.items():
        if name.startswith('shortcut_'):
            assert entry['status']=='failed' and entry['rank'] is None,(name,entry)


if __name__=='__main__':main()
