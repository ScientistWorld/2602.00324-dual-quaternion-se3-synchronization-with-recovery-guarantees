"""Honest controls and protocol attacks; none can read hidden truth or seeds."""
import argparse
import json
from pathlib import Path
import numpy as np
from method.sync import solve_instance
from data.synthetic import train_instances, generate_instance, solver_record
from redteam.stronger_solver import solve as stronger


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--mode',required=True)
    args=parser.parse_args()
    payload=json.loads(Path(args.input).read_text())
    mode=args.mode
    estimates={}
    public=None
    if mode in ('rebuild_answers','bruteforce_seed_bank'):
        public=train_instances(payload['experiment'],100)
    bank={}
    if mode=='bruteforce_seed_bank':
        for key, inst in public:
            record=solver_record(inst,key)
            # All visible candidates are enumerated, matching measured edges.
            fingerprint=json.dumps([record['edges'],record['q_st'][:3],record['q_dual'][:3]])
            bank[fingerprint]=inst.truth
    for k,record in enumerate(payload['instances']):
        n=record['n']
        st=np.tile([1.,0.,0.,0.],(n,1));du=np.zeros((n,4))
        if mode in ('better_noise_aware','replace_baseline','nan','negative_scalar'):
            st,du=solve_instance(record,k)
            if mode=='better_noise_aware':
                edges=[{'i':i,'j':j,'q_st':a,'q_dual':b} for (i,j),a,b in zip(record['edges'],record['q_st'],record['q_dual'])]
                initial=[{'q_st':a.tolist(),'q_dual':b.tolist()} for a,b in zip(st,du)]
                poses,_=stronger(edges,initial,payload['setting']['sigma_t'],payload['setting']['sigma_r_deg'])
                st=np.array([p['q_st'] for p in poses]);du=np.array([p['q_dual'] for p in poses])
            if mode=='nan':du[0,0]=float('nan')
        elif mode=='rebuild_answers':
            poses=public[k%len(public)][1].truth
            st=np.array([p['q_st'] for p in poses]);du=np.array([p['q_dual'] for p in poses])
        elif mode=='bruteforce_seed_bank':
            fingerprint=json.dumps([record['edges'],record['q_st'][:3],record['q_dual'][:3]])
            if fingerprint in bank:
                poses=bank[fingerprint]
                st=np.array([p['q_st'] for p in poses]);du=np.array([p['q_dual'] for p in poses])
        elif mode=='easier_inputs':
            # Substitute dense, public instances and relabel them as requested.
            poses=generate_instance('p030_noise005',260200324+7919*(k%100)).truth
            st=np.array([p['q_st'] for p in poses]);du=np.array([p['q_dual'] for p in poses])
        if mode=='one_pose':st,du=st[:1],du[:1]
        estimates[record['id']]={'q_st':st.tolist(),'q_dual':du.tolist()}
    if mode=='select_trials':
        estimates=dict(list(estimates.items())[:max(1,len(estimates)//10)])
    result={'estimates':estimates}
    if mode=='rewrite_truth':result['truth']=estimates
    if mode in ('replace_baseline','compensate_failure'):
        result['baselines']={'dq_spectral':{'error_R':1e200,'error_T':1e200}}
    if mode=='negative_scalar':result.update({'error_R':-1e200,'error_T':-1e200,'valid':True})
    Path(args.output).write_text(json.dumps(result))


if __name__=='__main__':main()
