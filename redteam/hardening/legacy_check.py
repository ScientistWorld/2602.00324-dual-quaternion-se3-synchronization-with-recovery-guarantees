"""Check that vectorization preserves the actual paper procedure, on the job."""
import json
from pathlib import Path
import numpy as np
from redteam.hardening import legacy_sync as old
from method import sync as new

report=[]
for noise in (0.,.1):
    legacy,_,_=old.build_synthetic_measurement(8,.7,noise,noise*100,123)
    edges=[];st=[];du=[]
    for i in range(8):
        for j in range(i+1,8):
            if j in legacy.neighbors[i]:
                edges.append([i,j]);st.append(legacy.c_st[:,i,j]);du.append(legacy.c_dual[:,i,j])
    current=new.MeasurementMatrix(8,edges,st,du)
    x=np.random.default_rng(1).normal(size=64)
    diff=float(np.max(np.abs(legacy.matvec(x)-current.matvec(x))))
    a,_,_=old.spectral_power_initializer(legacy,0)
    b,_,_=new.spectral_power_initializer(current,0)
    spectral=float(np.max(np.abs(a-b)))
    oa,_=old.dqgpm(legacy,a,max_iter=30)
    nb,_=new.dqgpm(current,b,max_iter=30)
    refined=float(np.max(np.abs(oa-nb)))
    assert diff<1e-10 and spectral<1e-8 and refined<1e-8,(diff,spectral,refined)
    report.append({'noise':noise,'matvec_max_difference':diff,'spectral_max_difference':spectral,'refined_max_difference':refined})
Path('redteam/hardening/algorithm_check.json').write_text(json.dumps(report,indent=2)+'\n')

# Output gauge fixing must preserve every measured relative pose exactly.
from method.dual_quaternion import quaternion_conjugate as qc, quaternion_multiply as qm
st,du=new.arrays_from_vector(nb)
cs,cd=new.center_translation_gauge(st,du)
relative_difference=0.
for i in range(len(st)):
    for j in range(len(st)):
        original=qm(st[i],qc(du[j]))+qm(du[i],qc(st[j]))
        centered=qm(cs[i],qc(cd[j]))+qm(cd[i],qc(cs[j]))
        relative_difference=max(relative_difference,float(np.max(np.abs(original-centered))))
assert relative_difference<1e-10,relative_difference
body=np.array([2.*qm(qc(q),d)[1:] for q,d in zip(cs,cd)])
assert np.linalg.norm(body.mean(axis=0))<1e-10
report.append({'gauge_relative_pose_max_difference':relative_difference,'gauge_body_translation_mean_norm':float(np.linalg.norm(body.mean(axis=0)))})
Path('redteam/hardening/algorithm_check.json').write_text(json.dumps(report,indent=2)+'\n')
