#!/usr/bin/env python3
"""Rounded dual-quaternion spectral estimator (paper Algorithm 1 + Eq. 2.3).

Power iteration on the Hermitian dual-quaternion measurement matrix until the
relative residual drops below 1e-5 (Section 4.2; capped at 2000 iterations),
followed by the elementwise projection onto UDQ^n.  This is the feasible
spectral estimator x~ = Pi(u_1) of Theorem 2.8, i.e. the paper's pipeline
without the iterative refinement stage.

    python3 -m baseline.dq_spectral --input in.json --output out.json
"""

from __future__ import annotations

import numpy as np

from baseline.common import CONJ, IDENTITY, instance_arrays, run_cli


def left_mul_matrices(q: np.ndarray) -> np.ndarray:
    w, x, y, z = np.moveaxis(np.asarray(q, dtype=np.float64), -1, 0)
    return np.stack(
        [
            np.stack([w, -x, -y, -z], axis=-1),
            np.stack([x, w, -z, y], axis=-1),
            np.stack([y, z, w, -x], axis=-1),
            np.stack([z, -y, x, w], axis=-1),
        ],
        axis=-2,
    )


def measurement_blocks(n, edges, c_st, c_dual):
    l_st = np.zeros((4 * n, 4 * n))
    l_dual = np.zeros((4 * n, 4 * n))
    for i in range(n):
        l_st[4 * i : 4 * i + 4, 4 * i : 4 * i + 4] = np.eye(4)
    if len(edges):
        a, b = left_mul_matrices(c_st), left_mul_matrices(c_dual)
        ac, bc = left_mul_matrices(c_st * CONJ), left_mul_matrices(c_dual * CONJ)
        for k, (i, j) in enumerate(edges):
            l_st[4 * i : 4 * i + 4, 4 * j : 4 * j + 4] = a[k]
            l_dual[4 * i : 4 * i + 4, 4 * j : 4 * j + 4] = b[k]
            l_st[4 * j : 4 * j + 4, 4 * i : 4 * i + 4] = ac[k]
            l_dual[4 * j : 4 * j + 4, 4 * i : 4 * i + 4] = bc[k]
    return l_st, l_dual


def _normalize(x: np.ndarray) -> np.ndarray:
    n4 = len(x) // 2
    st, dual = x[:n4], x[n4:]
    norm_sq = float(np.dot(st, st))
    if norm_sq < 1e-28:
        return x.copy()
    norm_st = float(np.sqrt(norm_sq))
    if norm_st < 1e-14:
        return x.copy()
    norm_dual = float(np.dot(st, dual) / norm_st)
    inv_st = 1.0 / norm_st
    inv_dual = -norm_dual / (norm_st * norm_st)
    return np.concatenate((inv_st * st, inv_st * dual + inv_dual * st))


def project(st: np.ndarray, dual: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Elementwise projection onto UDQ^n (Proposition 2.7)."""
    st_sq = np.einsum("ij,ij->i", st, st)
    dual_sq = np.einsum("ij,ij->i", dual, dual)
    zero = (st_sq < 1e-28) & (dual_sq < 1e-28)
    regular = st_sq > 1e-14
    out_st = np.tile(IDENTITY, (len(st), 1))
    out_dual = np.zeros_like(dual)
    norm = np.sqrt(np.where(regular, st_sq, 1.0))[:, None]
    u_st = st / norm
    u_dual = dual / norm
    u_dual = u_dual - np.einsum("ij,ij->i", u_st, u_dual)[:, None] * u_st
    out_st[regular], out_dual[regular] = u_st[regular], u_dual[regular]
    for i in np.flatnonzero(~zero & ~regular):
        dn = np.linalg.norm(dual[i])
        if dn > 1e-14:
            u = dual[i] / dn
            trial = np.array([0.0, 1.0, 0.0, 0.0])
            if abs(np.dot(trial, u)) > 0.9:
                trial = np.array([0.0, 0.0, 1.0, 0.0])
            v = trial - np.dot(trial, u) * u
            out_st[i], out_dual[i] = u, v / np.linalg.norm(v)
    nonzero = np.flatnonzero(~zero)
    if zero.any() and len(nonzero):
        out_st[zero], out_dual[zero] = out_st[nonzero[0]], out_dual[nonzero[0]]
    return out_st, out_dual


def solve(instance: dict, seed: int, tol: float = 1e-5, max_iter: int = 2000):
    n, edges, c_st, c_dual = instance_arrays(instance)
    l_st, l_dual = measurement_blocks(n, edges, c_st, c_dual)
    rng = np.random.default_rng(seed)
    x = _normalize(rng.normal(size=8 * n))
    n4 = 4 * n
    for _ in range(max_iter):
        y = np.concatenate((l_st @ x[:n4], l_st @ x[n4:] + l_dual @ x[:n4]))
        if np.sqrt(float(np.dot(y[:n4], y[:n4]))) < 1e-14:
            break
        x_next = _normalize(y)
        residual = np.linalg.norm(x_next - x) / max(np.linalg.norm(x), 1e-14)
        x = x_next
        if residual < tol:
            break
    x = np.sqrt(n) * x
    return project(x[:n4].reshape(n, 4), x[n4:].reshape(n, 4))


if __name__ == "__main__":
    run_cli(solve, __doc__.split("\n\n")[0])
