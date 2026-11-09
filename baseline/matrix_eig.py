#!/usr/bin/env python3
"""Matrix spectral SE(3) synchronization (EIG), the paper's matrix-based comparator.

Follows the spectral method of Arrigoni, Rossi and Fusiello (2016, SIAM J.
Imaging Sci.) that the paper compares against in Table 2:

1. Each observed relative dual quaternion is normalized onto UDQ and converted
   to its 4x4 homogeneous matrix M_ij = T_i T_j^{-1}; M_ji = M_ij^{-1}; M_ii = I.
2. With D = diag(degree_i + 1) (x) I_4, the 4 leading eigenvectors of D^{-1} X
   span the stacked poses [T_1; ...; T_n] up to a 4x4 invertible matrix.
3. Rounding: the basis is fixed so the average homogeneous row of the blocks is
   (0, 0, 0, 1); each 3x3 block is projected onto SO(3) (majority determinant
   sign fixed globally) and the last column gives the translation.

    python3 -m baseline.matrix_eig --input in.json --output out.json
"""

from __future__ import annotations

import numpy as np

from baseline.common import (
    dq_from_rotation_translation,
    instance_arrays,
    normalize_rows,
    qmul,
    quat_from_rotmat,
    rotmat_from_quat,
    run_cli,
)


def relative_transforms(c_st: np.ndarray, c_dual: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    st, dual = normalize_rows(c_st, c_dual)
    rot = rotmat_from_quat(st)
    trans = 2.0 * qmul(dual, st * np.array([1.0, -1.0, -1.0, -1.0]))[:, 1:]
    return rot, trans


def solve(instance: dict, seed: int = 0):
    del seed  # deterministic
    n, edges, c_st, c_dual = instance_arrays(instance)
    x = np.zeros((4 * n, 4 * n))
    degree = np.ones(n)
    for i in range(n):
        x[4 * i : 4 * i + 4, 4 * i : 4 * i + 4] = np.eye(4)
    if len(edges):
        rot, trans = relative_transforms(c_st, c_dual)
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
    gauge = np.vstack((vh[1:4], k4))
    v = u @ np.linalg.inv(gauge)
    blocks = v.reshape(n, 4, 4)
    if np.sum(np.sign(np.linalg.det(blocks[:, :3, :3]))) < 0:
        v[:, 0] *= -1.0
        blocks = v.reshape(n, 4, 4)
    uu, _, vv = np.linalg.svd(blocks[:, :3, :3])
    fix = np.ones((n, 3))
    fix[:, 2] = np.sign(np.linalg.det(uu @ vv))
    fix[fix[:, 2] == 0, 2] = 1.0
    rotations = uu @ (fix[:, :, None] * vv)
    translations = blocks[:, :3, 3].copy()
    q = quat_from_rotmat(rotations)
    bad = ~np.all(np.isfinite(q), axis=1) | ~np.all(np.isfinite(translations), axis=1)
    q[bad] = np.array([1.0, 0.0, 0.0, 0.0])
    translations[bad] = 0.0
    return dq_from_rotation_translation(q, translations)


if __name__ == "__main__":
    run_cli(solve, __doc__.split("\n\n")[0])
