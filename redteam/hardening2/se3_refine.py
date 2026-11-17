"""Honest stronger control for the real-scan experiments.

Starting from any estimate, minimize the weighted chordal SE(3) least-squares
objective (the maximum-likelihood objective of the declared rigid perturbation)

    sum_ij kappa ||R_j - R_i R_ij||_F^2 + tau ||t_j - t_i - R_i t_ij||^2

with Levenberg-Marquardt on SO(3)^n x R^3n. Inputs are measurements and the
declared noise levels only; no truth is used.
"""
from __future__ import annotations

import numpy as np

CONJ = np.array([1., -1., -1., -1.])


def qmul(p, q):
    pw, px, py, pz = np.moveaxis(np.asarray(p, float), -1, 0)
    qw, qx, qy, qz = np.moveaxis(np.asarray(q, float), -1, 0)
    return np.stack([pw*qw - px*qx - py*qy - pz*qz, pw*qx + px*qw + py*qz - pz*qy,
                     pw*qy - px*qz + py*qw + pz*qx, pw*qz + px*qy - py*qx + pz*qw], axis=-1)


def rotmat(q):
    q = np.asarray(q, float)
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    w, x, y, z = np.moveaxis(q, -1, 0)
    r = np.empty(q.shape[:-1] + (3, 3))
    r[..., 0, 0] = 1 - 2*(y*y + z*z); r[..., 0, 1] = 2*(x*y - w*z); r[..., 0, 2] = 2*(x*z + w*y)
    r[..., 1, 0] = 2*(x*y + w*z); r[..., 1, 1] = 1 - 2*(x*x + z*z); r[..., 1, 2] = 2*(y*z - w*x)
    r[..., 2, 0] = 2*(x*z - w*y); r[..., 2, 1] = 2*(y*z + w*x); r[..., 2, 2] = 1 - 2*(x*x + y*y)
    return r


def quat(r):
    out = []
    for m in np.asarray(r, float):
        tr = np.trace(m)
        cand = [1 + tr, 1 + m[0, 0] - m[1, 1] - m[2, 2], 1 - m[0, 0] + m[1, 1] - m[2, 2], 1 - m[0, 0] - m[1, 1] + m[2, 2]]
        k = int(np.argmax(cand))
        s = 0.5*np.sqrt(max(cand[k], 1e-300)); d = 4*s
        if k == 0:
            q = [s, (m[2, 1]-m[1, 2])/d, (m[0, 2]-m[2, 0])/d, (m[1, 0]-m[0, 1])/d]
        elif k == 1:
            q = [(m[2, 1]-m[1, 2])/d, s, (m[0, 1]+m[1, 0])/d, (m[0, 2]+m[2, 0])/d]
        elif k == 2:
            q = [(m[0, 2]-m[2, 0])/d, (m[0, 1]+m[1, 0])/d, s, (m[1, 2]+m[2, 1])/d]
        else:
            q = [(m[1, 0]-m[0, 1])/d, (m[0, 2]+m[2, 0])/d, (m[1, 2]+m[2, 1])/d, s]
        out.append(np.array(q)/np.linalg.norm(q))
    return np.array(out)


def skew(v):
    return np.array([[0., -v[2], v[1]], [v[2], 0., -v[0]], [-v[1], v[0], 0.]])


def expm(w):
    th = np.linalg.norm(w)
    if th < 1e-15:
        return np.eye(3) + skew(w)
    k = skew(w/th)
    return np.eye(3) + np.sin(th)*k + (1-np.cos(th))*k@k


def refine(record, st0, du0, sigma_t, sigma_r_deg, iterations=60):
    n = int(record['n'])
    edges = np.asarray(record['edges'], int).reshape(-1, 2)
    if not len(edges):
        return np.asarray(st0), np.asarray(du0)
    cq = np.asarray(record['q_st'], float)
    cd = np.asarray(record['q_dual'], float)
    s = np.linalg.norm(cq, axis=1, keepdims=True)
    cq, cd = cq/s, cd/s
    cd = cd - np.sum(cq*cd, axis=1, keepdims=True)*cq
    rm = rotmat(cq)
    tm = 2*qmul(cd, cq*CONJ)[:, 1:]
    q0 = np.asarray(st0, float); q0 = q0/np.linalg.norm(q0, axis=1, keepdims=True)
    rx = rotmat(q0)
    tx = 2*qmul(np.asarray(du0, float), q0*CONJ)[:, 1:]
    rot = np.transpose(rx, (0, 2, 1))           # T_i = X_i^-1
    tr = -np.einsum('nij,nj->ni', rot, tx)
    sk = np.sqrt(3.0/(2.0*np.deg2rad(sigma_r_deg)**2))
    stau = 1.0/sigma_t
    i, j = edges[:, 0], edges[:, 1]
    m = len(edges)
    gens = [skew(e) for e in np.eye(3)]

    def residual(rot, tr):
        a = sk*(rot[j] - rot[i]@rm)
        b = stau*(tr[j] - tr[i] - np.einsum('mij,mj->mi', rot[i], tm))
        return np.concatenate([a.reshape(m, 9), b], axis=1).reshape(-1)

    r = residual(rot, tr)
    cost = float(r@r)
    lam = 1e-3
    rows = np.arange(m)[:, None]*12
    for _ in range(iterations):
        jac = np.zeros((12*m, 6*n))
        for a, g in enumerate(gens):
            dj = sk*(rot[j]@g).reshape(m, 9)
            di = -sk*(rot[i]@g@rm).reshape(m, 9)
            dt = -stau*np.einsum('mij,mj->mi', rot[i]@g, tm)
            jac[rows + np.arange(9), (6*j + a)[:, None]] += dj
            jac[rows + np.arange(9), (6*i + a)[:, None]] += di
            jac[rows + 9 + np.arange(3), (6*i + a)[:, None]] += dt
        for a in range(3):
            jac[rows[:, 0] + 9 + a, 6*j + 3 + a] += stau
            jac[rows[:, 0] + 9 + a, 6*i + 3 + a] -= stau
        h = jac.T@jac
        g = jac.T@r
        improved = False
        for _ in range(12):
            step = -np.linalg.solve(h + lam*np.diag(np.diag(h)) + 1e-9*np.trace(h)/len(h)*np.eye(len(h)), g)
            step = step.reshape(n, 6)
            new_rot = np.stack([rot[k]@expm(step[k, :3]) for k in range(n)])
            new_tr = tr + step[:, 3:]
            new_r = residual(new_rot, new_tr)
            new_cost = float(new_r@new_r)
            if new_cost < cost:
                rel = (cost - new_cost)/max(cost, 1e-300)
                rot, tr, r, cost = new_rot, new_tr, new_r, new_cost
                lam = max(lam/3.0, 1e-9)
                improved = True
                break
            lam *= 5.0
        if not improved or rel < 1e-12:
            break
    rx = np.transpose(rot, (0, 2, 1))
    tx = -np.einsum('nij,nj->ni', rx, tr)
    q = quat(rx)
    du = 0.5*qmul(np.concatenate([np.zeros((n, 1)), tx], axis=1), q)
    return q, du
