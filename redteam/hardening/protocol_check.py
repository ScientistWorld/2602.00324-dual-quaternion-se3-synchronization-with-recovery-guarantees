"""Small adversarial assertions on scorer semantics, run with the joint job."""
import copy,importlib.util,json,sys
from pathlib import Path
report={}
for side in ('train','test'):
    spec=importlib.util.spec_from_file_location(f'check_{side}',f'eval/{side}/evaluate.py')
    e=importlib.util.module_from_spec(spec);sys.modules[spec.name]=e;spec.loader.exec_module(e)
    poses={'q_st':[[1.,0.,0.,0.]]*2,'q_dual':[[0.,0.,0.,0.]]*2}
    good={'estimates':{'0':poses}}
    truth=[('0',2,[([1.,0.,0.,0.],[0.,0.,0.])]*2)]
    assert e.score_output(good,truth)==([0.],[0.])
    cases={}
    cases['one_pose']=copy.deepcopy(good);cases['one_pose']['estimates']['0']['q_st']=poses['q_st'][:1]
    cases['missing_id']={'estimates':{}}
    cases['extra_id']=copy.deepcopy(good);cases['extra_id']['estimates']['extra']=poses
    for label,value in [('nan',float('nan')),('infinity',float('inf')),('overflow',10**400),('null',None),('bool',True)]:
        cases[label]=copy.deepcopy(good);cases[label]['estimates']['0']['q_dual'][0]=[value,0.,0.,0.]
    cases['nonunit']=copy.deepcopy(good);cases['nonunit']['estimates']['0']['q_st'][0]=[2.,0.,0.,0.]
    cases['nonorthogonal']=copy.deepcopy(good);cases['nonorthogonal']['estimates']['0']['q_dual'][0]=[1.,0.,0.,0.]
    cases['huge_translation']=copy.deepcopy(good);cases['huge_translation']['estimates']['0']['q_dual'][0]=[0.,1e7,0.,0.]
    cases['truth_forgery']={**good,'truth':{}}
    cases['baseline_forgery']={**good,'baselines':{}}
    rejected=[]
    for label,value in cases.items():
        try:e.score_output(value,truth)
        except e.InvalidOutput:rejected.append(label)
        else:raise AssertionError((side,label,'was accepted'))
    for text in ('{"estimates":{},"estimates":{}}','{"x":NaN}','{"x":Infinity}'):
        try:e.strict_json(text)
        except e.InvalidOutput:pass
        else:raise AssertionError('non-strict JSON accepted')
    cfg={'experiments':{'x':{'weight':1.,'metrics':{'a':{'coefficient':-2.,'higher_is_better':False},'b':{'coefficient':3.,'higher_is_better':True}}}}}
    anchor={'x':{'a':10.,'b':10.}}
    values={'better':{'x':{'a':8.,'b':12.}},'worse':{'x':{'a':12.,'b':8.}},'failed':{'x':{'a':0.,'b':1e200}}}
    statuses={n:{'status':'failed' if n=='failed' else 'ok'} for n in values}
    ranks,scales=e.normalized_ranks(values,statuses,anchor,cfg)
    assert ranks['better']>0>ranks['worse'] and ranks['failed'] is None
    scaled=copy.deepcopy(values);scaled_anchor=copy.deepcopy(anchor)
    for v in scaled.values():v['x']['a']*=1000
    scaled_anchor['x']['a']*=1000
    cfg['experiments']['x']['metrics']['a']['coefficient']=2.
    ranks2,_=e.normalized_ranks(scaled,statuses,scaled_anchor,cfg)
    assert abs(ranks['better']-ranks2['better'])<1e-12
    report[side]={'invalid_cases_rejected':rejected,'strict_json':True,'failed_rank':None,'direction_sign_and_units_invariant':True}
Path('redteam/hardening/protocol_check.json').write_text(json.dumps(report,indent=2)+'\n')
