"""Audit-only solvers: an honest stronger control and shortcut probes.

Modes
  better             synthetic: noise-aware quaternion/translation refinement
                     (redteam/stronger_solver.py); real scans: weighted SE(3)
                     maximum-likelihood refinement (se3_refine.py). Both start
                     from the reference estimate and never see truth.
  pool               average the measurements of all trials that share an
                     identical measurement graph, solve once, reuse the answer.
  public_truth       real scans: return the repository's published alignment
                     in file order (what hard-coding public answers gives).
  zero_translation   real scans: reference rotations with all translations 0.
  isolated_identity  synthetic: reference, but nodes without measurements get
                     the identity pose (the prior mean of an unidentifiable pose).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from method.sync import solve_instance
from redteam.stronger_solver import solve as stronger
from redteam.hardening2.se3_refine import qmul, refine


def reference(record, k):
    return solve_instance(record, k)


def public_configs(mode):
    configs = []
    for side in ('test', 'train'):
        path = Path('eval') / side / 'scans.json'
        if path.is_file():
            configs += [c for c in json.loads(path.read_text())['configs'] if c['mode'] == mode]
    return configs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--mode', required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text())
    setting = payload['setting']
    scans = setting.get('source') == 'stanford_scans'
    mode = args.mode
    estimates = {}
    records = payload['instances']
    if mode == 'pool':
        groups = {}
        for k, rec in enumerate(records):
            groups.setdefault(json.dumps([rec['n'], rec['edges']]), []).append(k)
        for members in groups.values():
            base = records[members[0]]
            st = np.zeros((len(base['edges']), 4))
            du = np.zeros((len(base['edges']), 4))
            first = np.asarray(base['q_st'], float)
            for k in members:
                a = np.asarray(records[k]['q_st'], float)
                b = np.asarray(records[k]['q_dual'], float)
                sign = np.where(np.sum(a*first, axis=1) < 0, -1.0, 1.0)[:, None]
                st += sign*a
                du += sign*b
            pooled = {**base, 'q_st': (st/len(members)).tolist(), 'q_dual': (du/len(members)).tolist()}
            q, d = reference(pooled, members[0])
            for k in members:
                estimates[records[k]['id']] = {'q_st': q.tolist(), 'q_dual': d.tolist()}
    else:
        for k, rec in enumerate(records):
            n = rec['n']
            if mode == 'public_truth' and scans:
                matches = [c for c in public_configs(setting['graph'])
                           if c['n'] == n and len(c['edges']) == len(rec['edges'])]
                rows = np.array(matches[0]['truth']) if matches else np.tile([1., 0, 0, 0, 0, 0, 0], (n, 1))
                q = rows[:, :4]
                d = 0.5*qmul(np.concatenate([np.zeros((n, 1)), rows[:, 4:]], axis=1), q)
            else:
                q, d = reference(rec, k)
                if mode == 'better':
                    if scans:
                        q, d = refine(rec, q, d, setting['sigma_t'], setting['sigma_r_deg'])
                    else:
                        edges = [{'i': i, 'j': j, 'q_st': a, 'q_dual': b}
                                 for (i, j), a, b in zip(rec['edges'], rec['q_st'], rec['q_dual'])]
                        initial = [{'q_st': a.tolist(), 'q_dual': b.tolist()} for a, b in zip(q, d)]
                        poses, _ = stronger(edges, initial, setting['sigma_t'], setting['sigma_r_deg'])
                        q = np.array([p['q_st'] for p in poses])
                        d = np.array([p['q_dual'] for p in poses])
                elif mode == 'zero_translation' and scans:
                    d = np.zeros_like(np.asarray(d))
                elif mode == 'isolated_identity' and not scans:
                    degree = np.zeros(n, int)
                    for i, j in rec['edges']:
                        degree[i] += 1
                        degree[j] += 1
                    q, d = np.array(q), np.array(d)
                    q[degree == 0] = [1., 0., 0., 0.]
                    d[degree == 0] = 0.
            estimates[rec['id']] = {'q_st': np.asarray(q).tolist(), 'q_dual': np.asarray(d).tolist()}
    Path(args.output).write_text(json.dumps({'estimates': estimates}))


if __name__ == '__main__':
    main()
