"""Honest noise-aware quaternion refinement and translation estimation.

The solver receives only noisy edges and initial estimates, never truth.
The scalar and vector components of additive quaternion noise have different
variances; weighted nonlinear least squares accounts for this. Translation is
then estimated from every observed dual component with a Gaussian-prior ridge.
"""
from __future__ import annotations

import numpy as np


def mul(p, q):
    p, q = np.broadcast_arrays(np.asarray(p), np.asarray(q))
    w = p[..., :1]*q[..., :1] - np.sum(p[..., 1:]*q[..., 1:], axis=-1, keepdims=True)
    v = p[..., :1]*q[..., 1:] + q[..., :1]*p[..., 1:] + np.cross(p[..., 1:], q[..., 1:])
    return np.concatenate((w, v), axis=-1)


def conj(q):
    return np.asarray(q) * np.array([1., -1., -1., -1.])


def solve(measurements, initial, sigma_t, sigma_r_deg, iterations=10):
    q = np.array([pose['q_st'] for pose in initial], dtype=float)
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    n = len(q)
    edges = [edge for edge in measurements if edge['i'] != edge['j']]
    ii = np.array([e['i'] for e in edges])
    jj = np.array([e['j'] for e in edges])
    obs = np.array([e['q_st'] for e in edges])
    dual = np.array([e['q_dual'] for e in edges])
    m = len(edges)
    sigma = np.deg2rad(sigma_r_deg)
    target = obs.copy()
    target[:, 0] += 1. - np.exp(-sigma**2 / 8.)
    scalar_var = (1. + np.exp(-sigma**2 / 2.))/2. - np.exp(-sigma**2 / 4.)
    vector_var = (1. - np.exp(-sigma**2 / 2.)) / 6.
    weights = np.array([np.sqrt(vector_var / max(scalar_var, 1e-12)), 1., 1., 1.])
    basis = np.eye(4)[1:]
    rows = np.arange(4*m).reshape(m, 4)
    history = []
    for _ in range(iterations):
        rel = mul(q[ii], conj(q[jj]))
        residual = ((rel-target) * weights).reshape(-1)
        jac = np.zeros((4*m, 3*n))
        for a in range(3):
            jac[rows, (3*ii+a)[:, None]] = .5 * mul(basis[a], rel) * weights
            jac[rows, (3*jj+a)[:, None]] = -.5 * mul(rel, basis[a]) * weights
        delta = np.linalg.solve(jac.T @ jac + 1e-5*np.eye(3*n), -jac.T @ residual).reshape(n, 3)
        sizes = np.linalg.norm(delta, axis=1)
        delta *= np.minimum(1., .3 / np.maximum(sizes, 1e-15))[:, None]
        objective = float(residual @ residual)
        accepted = False
        for step in (1., .5, .25, .125, .0625):
            half = step * delta / 2.
            angles = np.linalg.norm(half, axis=1)
            update = np.concatenate((np.cos(angles)[:, None], half*np.sinc(angles[:, None]/np.pi)), axis=1)
            candidate = mul(update, q)
            candidate /= np.linalg.norm(candidate, axis=1, keepdims=True)
            next_residual = ((mul(candidate[ii], conj(candidate[jj]))-target)*weights).reshape(-1)
            if next_residual @ next_residual <= objective:
                q = candidate
                accepted = True
                break
        history.append(objective)
        if not accepted or np.max(np.abs(delta)) < 1e-7:
            break
    rel = mul(q[ii], conj(q[jj]))
    matrix = np.zeros((4*m, 3*n))
    for a in range(3):
        matrix[rows, (3*ii+a)[:, None]] = mul(basis[a], rel)
        matrix[rows, (3*jj+a)[:, None]] = -mul(rel, basis[a])
    translations = np.linalg.solve(
        matrix.T @ matrix + max(sigma_t**2, 1e-6)*np.eye(3*n),
        matrix.T @ (2*dual).reshape(-1),
    ).reshape(n, 3)
    dq = .5*mul(np.concatenate((np.zeros((n, 1)), translations), axis=1), q)
    return [{'q_st': r.tolist(), 'q_dual': d.tolist()} for r, d in zip(q, dq)], history
