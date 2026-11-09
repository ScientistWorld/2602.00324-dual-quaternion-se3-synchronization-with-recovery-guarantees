"""Evaluator-owned comparators for the hidden test (no agent-writable code).

* ``dq_spectral``: the paper's rounded dual-quaternion spectral estimator
  (Algorithm 1 power iteration to residual 1e-5, capped at 2000 iterations,
  then the elementwise projection onto UDQ^n of Proposition 2.7).
* ``matrix_eig``: the matrix spectral SE(3) method (EIG) of Arrigoni, Rossi and
  Fusiello (2016) that the paper compares against: 4 leading eigenvectors of
  D^{-1} X with X the 4x4-block matrix of relative homogeneous transforms,
  rounded by fixing the mean homogeneous row and projecting blocks to SE(3).

Both run on the same in-memory measurements every submitted solver receives.
"""

from __future__ import annotations

import numpy as np

_CONJ = np.array([1.0, -1.0, -1.0, -1.0])
_IDENTITY = np.array([1.0, 0.0, 0.0, 0.0])


def _qmul(p, q):
    pw, px, py, pz = np.moveaxis(np.asarray(p, dtype=np.float64), -1, 0)
    qw, qx, qy, qz = np.moveaxis(np.asarray(q, dtype=np.float64), -1, 0)
    return np.stack(
        [
            pw * qw - px * qx - py * qy - pz * qz,
            pw * qx + px * qw + py * qz - pz * qy,
            pw * qy - px * qz + py * qw + pz * qx,
            pw * qz + px * qy - py * qx + pz * qw,
        ],
        axis=-1,
    )


def _left(q):
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


def _arrays(instance):
    n = int(instance["n"])
    edges = np.asarray(instance["edges"], dtype=np.int64).reshape(-1, 2)
    c_st = np.asarray(instance["q_st"], dtype=np.float64).reshape(-1, 4)
    c_dual = np.asarray(instance["q_dual"], dtype=np.float64).reshape(-1, 4)
    return n, edges, c_st, c_dual


# ── dual-quaternion spectral estimator ──────────────────────────────────────


def _dq_normalize(x):
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


def _project(st, dual):
    st_sq = np.einsum("ij,ij->i", st, st)
    dual_sq = np.einsum("ij,ij->i", dual, dual)
    zero = (st_sq < 1e-28) & (dual_sq < 1e-28)
    regular = st_sq > 1e-14
    out_st = np.tile(_IDENTITY, (len(st), 1))
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


def dq_spectral(instance, seed, tol=1e-5, max_iter=2000):
    n, edges, c_st, c_dual = _arrays(instance)
    l_st = np.zeros((4 * n, 4 * n))
    l_dual = np.zeros((4 * n, 4 * n))
    for i in range(n):
        l_st[4 * i : 4 * i + 4, 4 * i : 4 * i + 4] = np.eye(4)
    if len(edges):
        a, b = _left(c_st), _left(c_dual)
        ac, bc = _left(c_st * _CONJ), _left(c_dual * _CONJ)
        for k, (i, j) in enumerate(edges):
            l_st[4 * i : 4 * i + 4, 4 * j : 4 * j + 4] = a[k]
            l_dual[4 * i : 4 * i + 4, 4 * j : 4 * j + 4] = b[k]
            l_st[4 * j : 4 * j + 4, 4 * i : 4 * i + 4] = ac[k]
            l_dual[4 * j : 4 * j + 4, 4 * i : 4 * i + 4] = bc[k]
    rng = np.random.default_rng(seed)
    x = _dq_normalize(rng.normal(size=8 * n))
    n4 = 4 * n
    for _ in range(max_iter):
        y = np.concatenate((l_st @ x[:n4], l_st @ x[n4:] + l_dual @ x[:n4]))
        if np.sqrt(float(np.dot(y[:n4], y[:n4]))) < 1e-14:
            break
        x_next = _dq_normalize(y)
        residual = np.linalg.norm(x_next - x) / max(np.linalg.norm(x), 1e-14)
        x = x_next
        if residual < tol:
            break
    x = np.sqrt(n) * x
    return _project(x[:n4].reshape(n, 4), x[n4:].reshape(n, 4))


# ── matrix spectral EIG ─────────────────────────────────────────────────────


def _rotmat(q):
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    w, x, y, z = np.moveaxis(q, -1, 0)
    r = np.empty(q.shape[:-1] + (3, 3))
    r[..., 0, 0] = 1 - 2 * (y * y + z * z)
    r[..., 0, 1] = 2 * (x * y - w * z)
    r[..., 0, 2] = 2 * (x * z + w * y)
    r[..., 1, 0] = 2 * (x * y + w * z)
    r[..., 1, 1] = 1 - 2 * (x * x + z * z)
    r[..., 1, 2] = 2 * (y * z - w * x)
    r[..., 2, 0] = 2 * (x * z - w * y)
    r[..., 2, 1] = 2 * (y * z + w * x)
    r[..., 2, 2] = 1 - 2 * (x * x + y * y)
    return r


def _quat(r):
    out = np.empty(r.shape[:-2] + (4,))
    r00, r11, r22 = r[..., 0, 0], r[..., 1, 1], r[..., 2, 2]
    cand = np.stack([1 + r00 + r11 + r22, 1 + r00 - r11 - r22, 1 - r00 + r11 - r22, 1 - r00 - r11 + r22], axis=-1)
    k = np.argmax(cand, axis=-1)
    big = 0.5 * np.sqrt(np.maximum(np.take_along_axis(cand, k[..., None], -1)[..., 0], 1e-300))
    d = 4.0 * big
    a = (r[..., 2, 1] - r[..., 1, 2]) / d
    b = (r[..., 0, 2] - r[..., 2, 0]) / d
    c = (r[..., 1, 0] - r[..., 0, 1]) / d
    xy = (r[..., 0, 1] + r[..., 1, 0]) / d
    xz = (r[..., 0, 2] + r[..., 2, 0]) / d
    yz = (r[..., 1, 2] + r[..., 2, 1]) / d
    out[..., 0] = np.choose(k, [big, a, b, c])
    out[..., 1] = np.choose(k, [a, big, xy, xz])
    out[..., 2] = np.choose(k, [b, xy, big, yz])
    out[..., 3] = np.choose(k, [c, xz, yz, big])
    return out / np.linalg.norm(out, axis=-1, keepdims=True)


def matrix_eig(instance, seed=0):
    del seed
    n, edges, c_st, c_dual = _arrays(instance)
    x = np.zeros((4 * n, 4 * n))
    degree = np.ones(n)
    for i in range(n):
        x[4 * i : 4 * i + 4, 4 * i : 4 * i + 4] = np.eye(4)
    if len(edges):
        st_sq = np.einsum("ij,ij->i", c_st, c_st)
        ok = st_sq > 1e-14
        nrm = np.sqrt(np.where(ok, st_sq, 1.0))[:, None]
        st = np.where(ok[:, None], c_st / nrm, _IDENTITY)
        du = np.where(ok[:, None], c_dual / nrm, 0.0)
        du = du - np.einsum("ij,ij->i", st, du)[:, None] * st
        rot = _rotmat(st)
        trans = 2.0 * _qmul(du, st * _CONJ)[:, 1:]
        for k, (i, j) in enumerate(edges):
            m = np.eye(4)
            m[:3, :3] = rot[k]
            m[:3, 3] = trans[k]
            m_inv = np.eye(4)
            m_inv[:3, :3] = rot[k].T
            m_inv[:3, 3] = -rot[k].T @ trans[k]
            x[4 * i : 4 * i + 4, 4 * j : 4 * j + 4] = m
            x[4 * j : 4 * j + 4, 4 * i : 4 * i + 4] = m_inv
            degree[i] += 1
            degree[j] += 1
    a = x / np.repeat(degree, 4)[:, None]
    eigvals, eigvecs = np.linalg.eig(a)
    order = np.argsort(-eigvals.real, kind="stable")[:4]
    basis = np.concatenate((eigvecs[:, order].real, eigvecs[:, order].imag), axis=1)
    left, _, _ = np.linalg.svd(basis, full_matrices=False)
    u = left[:, :4]
    homogeneous = u[3::4, :]
    k4 = homogeneous.mean(axis=0)
    if np.linalg.norm(k4) < 1e-12:
        _, _, vh = np.linalg.svd(homogeneous)
        k4 = vh[0]
    _, _, vh = np.linalg.svd(k4[None, :])
    v = u @ np.linalg.inv(np.vstack((vh[1:4], k4)))
    blocks = v.reshape(n, 4, 4)
    if np.sum(np.sign(np.linalg.det(blocks[:, :3, :3]))) < 0:
        v[:, 0] *= -1.0
        blocks = v.reshape(n, 4, 4)
    uu, _, vv = np.linalg.svd(blocks[:, :3, :3])
    fix = np.ones((n, 3))
    fix[:, 2] = np.sign(np.linalg.det(uu @ vv))
    fix[fix[:, 2] == 0, 2] = 1.0
    q = _quat(uu @ (fix[:, :, None] * vv))
    t = blocks[:, :3, 3].copy()
    bad = ~np.all(np.isfinite(q), axis=1) | ~np.all(np.isfinite(t), axis=1)
    q[bad] = _IDENTITY
    t[bad] = 0.0
    t_quat = np.concatenate((np.zeros((n, 1)), t), axis=1)
    return q, 0.5 * _qmul(t_quat, q)


COMPARATORS = {"dq_spectral": dq_spectral, "matrix_eig": matrix_eig}
