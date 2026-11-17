"""Before-fix diagnostics for the shortcuts this hardening closes.

1. Unconditioned synthetic graphs (the previous generator): how much a
   hand-written guess for unidentifiable isolated nodes gains over the
   reference, and how much of matrix EIG's earlier translation advantage that
   guess explains.
2. Real scans in their native frames with fixed labels (a naive design):
   what pooling trials, hard-coding the published alignment, and zeroing all
   translations would score against the reference.
Writes redteam/hardening2/diag_before.json. Audit-only; never part of scoring.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from method.sync import solve_instance
from data.synthetic import sample_pose, sample_noise, dq_mul, dq_conj
from redteam.hardening2.se3_refine import qmul, rotmat


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


EV = load('eval/test/evaluate.py', 'audit_eval_test')
CMP = load('eval/test/comparators.py', 'audit_cmp_test')


def score(truth, st, du):
    est = [EV.pose(list(map(float, a)), list(map(float, b))) for a, b in zip(st, du)]
    return EV.aligned_errors(truth, est)


def old_synthetic(seed, n=100, p=0.05, sigma_t=0.05, sigma_r=5.0):
    rng = np.random.default_rng(seed)
    poses = [sample_pose(rng) for _ in range(n)]
    edges, q_st, q_dual = [], [], []
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() > p:
                continue
            rel = dq_mul(poses[i], dq_conj(poses[j]))
            noise = sample_noise(rng, sigma_t, sigma_r)
            edges.append([i, j])
            q_st.append((rel[0] + noise[0] - np.array([1., 0, 0, 0])).tolist())
            q_dual.append((rel[1] + noise[1]).tolist())
    truth = [EV.pose(a.tolist(), b.tolist()) for a, b in poses]
    return {'id': str(seed), 'n': n, 'edges': edges, 'q_st': q_st, 'q_dual': q_dual}, truth


def synthetic_part(trials=150):
    rows = {'reference': [], 'isolated_identity': [], 'matrix_eig_per_component': []}
    isolated_trials = 0
    for k in range(trials):
        rec, truth = old_synthetic(777000 + k)
        deg = np.zeros(rec['n'], int)
        for i, j in rec['edges']:
            deg[i] += 1
            deg[j] += 1
        isolated_trials += int((deg == 0).any())
        st, du = solve_instance(rec, k)
        rows['reference'].append(score(truth, st, du))
        st2, du2 = np.array(st), np.array(du)
        st2[deg == 0] = [1., 0, 0, 0]
        du2[deg == 0] = 0.
        rows['isolated_identity'].append(score(truth, st2, du2))
        st3, du3 = CMP.matrix_eig(rec, k)
        rows['matrix_eig_per_component'].append(score(truth, st3, du3))
    out = {'trials': trials, 'trials_with_isolated_nodes': isolated_trials, 'mean': {}, 'paired_gain_vs_reference': {}}
    ref = np.array(rows['reference'])
    for name, vals in rows.items():
        vals = np.array(vals)
        out['mean'][name] = {'error_R': float(vals[:, 0].mean()), 'error_T': float(vals[:, 1].mean())}
        delta = ref - vals
        out['paired_gain_vs_reference'][name] = {'error_R': float(delta[:, 0].mean()), 'error_T': float(delta[:, 1].mean()),
                                                 'error_T_se': float(delta[:, 1].std(ddof=1)/np.sqrt(len(delta)))}
    return out


def native_scan_trials(config, trials, seed):
    rng = np.random.default_rng(seed)
    truth = [(list(map(float, r[:4])), list(map(float, r[4:]))) for r in config['truth']]
    out = []
    for _ in range(trials):
        st, du = [], []
        for row in config['relative']:
            q, t = np.array(row[:4]), np.array(row[4:])
            axis = rng.normal(size=3)
            axis /= np.linalg.norm(axis)
            ang = np.deg2rad(rng.normal(0.0, EV.SCAN_SIGMA_R_DEG))
            nt = rng.normal(0.0, EV.SCAN_SIGMA_T, 3)
            cq = qmul(q, np.array([np.cos(ang/2), *(np.sin(ang/2)*axis)]))
            ct = rotmat(q) @ nt + t
            st.append(cq.tolist())
            du.append((0.5*qmul(np.array([0., *ct]), cq)).tolist())
        out.append({'id': '0', 'n': config['n'], 'edges': config['edges'], 'q_st': st, 'q_dual': du})
    return out, truth


def scan_part(trials=30):
    data = json.loads(Path('eval/test/scans.json').read_text())
    result = {}
    for c, config in enumerate(data['configs']):
        recs, truth = native_scan_trials(config, trials, 888000 + c)
        rows = {'reference': [], 'pool_trials': [], 'public_truth': [], 'zero_translation': []}
        q_pub = np.array([r[0] for r in truth])
        d_pub = 0.5*qmul(np.concatenate([np.zeros((len(truth), 1)), np.array([r[1] for r in truth])], axis=1), q_pub)
        pooled = {**recs[0], 'q_st': np.mean([r['q_st'] for r in recs], axis=0).tolist(),
                  'q_dual': np.mean([r['q_dual'] for r in recs], axis=0).tolist()}
        pst, pdu = solve_instance(pooled, 0)
        for k, rec in enumerate(recs):
            st, du = solve_instance(rec, k)
            rows['reference'].append(score(truth, st, du))
            rows['pool_trials'].append(score(truth, pst, pdu))
            rows['public_truth'].append(score(truth, q_pub, d_pub))
            rows['zero_translation'].append(score(truth, st, np.zeros_like(du)))
        result[config['name']] = {name: {'error_R': float(np.mean([v[0] for v in vals])),
                                         'error_T': float(np.mean([v[1] for v in vals]))} for name, vals in rows.items()}
    return {'trials_per_config': trials, 'configs': result}


def main():
    report = {'synthetic_unconditioned_p005_noise005': synthetic_part(), 'scans_native_frames': scan_part()}
    Path('redteam/hardening2/diag_before.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
