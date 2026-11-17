#!/usr/bin/env python3
"""Semidefinite relaxation (SDR) for SE(3) synchronization: SE-Sync (Rosen et al., 2019).

The paper compares against this method on the real-scan experiments (Table 4).
Translations are eliminated in closed form; the rotation SDP
min tr(Q Z) s.t. Z >= 0, Z_ii = I_3 is solved by ADMM on its dual, rounded as
in SE-Sync (top-3 eigenvectors, majority determinant sign, per-block SO(3)
projection), and translations are recovered by least squares. Measurement
weights follow the declared perturbation in the input ``setting``:
kappa = 3 / (2 sigma_r^2), tau = 1 / sigma_t^2. Identical to the frozen
evaluator comparator ``sdr``.

    python3 -m baseline.sdr --input in.json --output out.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from baseline.common import (
    center_translation_gauge,
    dq_from_rotation_translation,
    instance_arrays,
    quat_from_rotmat,
)
from baseline.matrix_eig import relative_transforms


def _project_so3(m: np.ndarray) -> np.ndarray:
    u, _, vt = np.linalg.svd(m)
    d = np.diag([1.0, 1.0, np.sign(np.linalg.det(u @ vt)) or 1.0])
    return u @ d @ vt


def _sdp_admm(q: np.ndarray, n: int, d: int = 3, tol: float = 1e-7, max_iter: int = 10000):
    scale = max(float(np.max(np.abs(q))), 1e-300)
    c = q / scale
    size = n * d
    x = np.eye(size)
    s = np.zeros((size, size))
    mu = 1.0
    blocks = [slice(d * i, d * i + d) for i in range(n)]
    eye = np.eye(d)
    for it in range(max_iter):
        # multiplier update on the diagonal blocks (A A^* = identity)
        lam = np.zeros((size, size))
        for b in blocks:
            blk = mu * (eye - x[b, b]) - (s[b, b] - c[b, b])
            lam[b, b] = 0.5 * (blk + blk.T)
        v = c - lam - mu * x
        v = 0.5 * (v + v.T)
        w, u = np.linalg.eigh(v)
        s = (u * np.maximum(w, 0.0)) @ u.T
        x_new = (s - v) / mu
        primal = max(float(np.max(np.abs(x_new[b, b] - eye))) for b in blocks)
        dual = float(np.max(np.abs(lam + s - c)))
        x = x_new
        if primal < tol and dual < tol:
            break
        if it % 50 == 49:
            # 1/mu penalizes dual infeasibility; mu weights primal infeasibility.
            if primal > 10.0 * dual:
                mu = min(mu * 2.0, 1e6)
            elif dual > 10.0 * primal:
                mu = max(mu / 2.0, 1e-6)
    return 0.5 * (x + x.T)


def sdr(instance: dict, seed: int = 0, setting: dict | None = None):
    del seed
    setting = setting or {}
    n, edges, st, dual = instance_arrays(instance)
    rot, trans = relative_transforms(st, dual)
    sigma_r = np.deg2rad(float(setting.get("sigma_r_deg") or 1.0))
    sigma_t = float(setting.get("sigma_t") or 1.0)
    kappa = 3.0 / (2.0 * sigma_r ** 2)
    tau = 1.0 / sigma_t ** 2
    d = 3
    lg = np.zeros((d * n, d * n))
    sig = np.zeros((d * n, d * n))
    v = np.zeros((n, d * n))
    lw = np.zeros((n, n))
    # Measurement C_ij = T_i^-1 T_j for node poses T_i (scan to world).
    for k, (i, j) in enumerate(edges):
        r, t = rot[k], trans[k]
        bi, bj = slice(d * i, d * i + d), slice(d * j, d * j + d)
        lg[bi, bi] += kappa * np.eye(d)
        lg[bj, bj] += kappa * np.eye(d)
        lg[bi, bj] -= kappa * r
        lg[bj, bi] -= kappa * r.T
        lw[i, i] += tau
        lw[j, j] += tau
        lw[i, j] -= tau
        lw[j, i] -= tau
        v[i, bi] += tau * t
        v[j, bi] -= tau * t
        sig[bi, bi] += tau * np.outer(t, t)
    lw_pinv = np.linalg.pinv(lw)
    q = lg + sig - v.T @ lw_pinv @ v
    q = 0.5 * (q + q.T)
    z = _sdp_admm(q, n, d)
    w, u = np.linalg.eigh(z)
    top = np.argsort(w)[::-1][:d]
    y = np.sqrt(np.maximum(w[top], 0.0))[:, None] * u[:, top].T
    dets = [np.linalg.det(y[:, d * i:d * i + d]) for i in range(n)]
    if sum(1 for x in dets if x > 0) < n / 2.0:
        y = np.diag([1.0, 1.0, -1.0]) @ y
    rotations = np.stack([_project_so3(y[:, d * i:d * i + d]) for i in range(n)])
    big = np.concatenate(list(rotations), axis=1)
    translations = (-big @ v.T @ lw_pinv).T
    # Output X_i = T_i^-1 (world to node frame) as unit dual quaternions.
    rx = np.transpose(rotations, (0, 2, 1))
    tx = -np.einsum("nij,nj->ni", rx, translations)
    return center_translation_gauge(*dq_from_rotation_translation(quat_from_rotmat(rx), tx))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text())
    estimates = {}
    for index, instance in enumerate(payload["instances"]):
        q_st, q_dual = sdr(instance, index, payload.get("setting"))
        estimates[instance["id"]] = {"q_st": np.asarray(q_st).tolist(), "q_dual": np.asarray(q_dual).tolist()}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"estimates": estimates}))


if __name__ == "__main__":
    main()
