#!/usr/bin/env python3
"""Matrix spectral SE(3) synchronization (EIG), the paper's matrix-based comparator.

Follows the spectral method of Arrigoni, Rossi and Fusiello (2016, SIAM J.
Imaging Sci.) that the paper compares against in Table 2:

1. Each observed relative dual quaternion is normalized onto UDQ and converted
   to its 4x4 homogeneous matrix M_ij = T_i T_j^{-1}; M_ji = M_ij^{-1}; No diagonal edges are added.
2. With D = diag(degree_i) (x) I_4, the 4 leading eigenvectors of D^{-1} X
   span the stacked poses [T_1; ...; T_n] up to a 4x4 invertible matrix.
3. Rounding solves BU alpha=0 for three columns and BU beta=1 for the
   homogeneous column, then projects each 3x3 block onto SO(3), with one global
   determinant-sign correction. Disconnected components are solved separately.

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


def _component_solve(n, edges, c_st, c_dual):
    x = np.zeros((4*n, 4*n))
    degree = np.zeros(n)
    rot, trans = relative_transforms(c_st, c_dual)
    for k, (i, j) in enumerate(edges):
        m, inv = np.eye(4), np.eye(4)
        m[:3, :3], m[:3, 3] = rot[k], trans[k]
        inv[:3, :3], inv[:3, 3] = rot[k].T, -rot[k].T @ trans[k]
        x[4*i:4*i+4, 4*j:4*j+4] = m
        x[4*j:4*j+4, 4*i:4*i+4] = inv
        degree[i] += 1
        degree[j] += 1
    vals, vecs = np.linalg.eig(x / np.repeat(degree, 4)[:, None])
    u, _ = np.linalg.qr(vecs[:, np.argsort(-vals.real, kind="stable")[:4]])
    u *= np.sqrt(n)
    # B selects all fourth rows: BU alpha=0, BU beta=1 (paper Eq. 9).
    bu = u[3::4]
    _, _, vh = np.linalg.svd(bu, full_matrices=True)
    alpha = vh.conj().T[:, -3:]
    beta = np.linalg.lstsq(bu, np.ones(n), rcond=None)[0]
    v = (u @ np.column_stack((alpha, beta))).real
    blocks = v.reshape(n, 4, 4)
    if np.sum(np.sign(np.linalg.det(blocks[:, :3, :3]))) < 0:
        blocks[:, :3, 0] *= -1
    uu, _, vv = np.linalg.svd(blocks[:, :3, :3])
    fix = np.ones((n, 3))
    fix[:, 2] = np.where(np.linalg.det(uu @ vv) < 0, -1., 1.)
    rotations = uu @ (fix[:, :, None] * vv)
    return quat_from_rotmat(rotations), blocks[:, :3, 3].copy()


def solve(instance: dict, seed: int = 0):
    del seed
    n, edges, st, dual = instance_arrays(instance)
    # EIG assumes a connected graph. Apply it separately to each connected
    # component; an unobserved pose has the identity estimate. No truth used.
    adjacency = [[] for _ in range(n)]
    for i, j in edges:
        adjacency[i].append(j)
        adjacency[j].append(i)
    q = np.tile([1., 0., 0., 0.], (n, 1))
    t = np.zeros((n, 3))
    unseen = set(range(n))
    while unseen:
        component, pending = [], [min(unseen)]
        unseen.remove(pending[0])
        while pending:
            i = pending.pop()
            component.append(i)
            for j in adjacency[i]:
                if j in unseen:
                    unseen.remove(j)
                    pending.append(j)
        if len(component) == 1:
            continue
        component.sort()
        mapping = {old: new for new, old in enumerate(component)}
        indices = [k for k, (i, j) in enumerate(edges) if i in mapping and j in mapping]
        local = np.array([[mapping[int(edges[k, 0])], mapping[int(edges[k, 1])]] for k in indices])
        q[component], t[component] = _component_solve(len(component), local, st[indices], dual[indices])
    return dq_from_rotation_translation(q, t)


if __name__ == "__main__":
    run_cli(solve, __doc__.split("\n\n")[0])
