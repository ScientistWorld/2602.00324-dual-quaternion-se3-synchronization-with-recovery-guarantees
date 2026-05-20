"""
SE(3) Synchronization via Dual Quaternions.

Implements the two-stage algorithm from:
"Dual Quaternion SE(3) Synchronization with Recovery Guarantees"
Zhao, Zhu, So (2026)

Approach:
- Represent poses as unit dual quaternions (rotation + translation)
- Build Hermitian dual quaternion measurement matrix C = x x* + noise
- Two-stage: spectral initializer + DQGPM refinement
"""

import numpy as np
from dual_quaternion import (
    quaternion_multiply, quaternion_conjugate, quaternion_inner_product,
    normalize_quaternion, normalize_dual_quaternion, DualQuaternion,
    sample_random_unit_dual_quaternion, sample_random_noise_dual_quaternion,
    rotation_error, translation_error, dual_quaternion_multiply
)


def dual_quaternion_conjugate(dq):
    """Dual quaternion conjugate: x* = q_st* - ε·q_dual*.
    For unit dual quaternions, this equals the group inverse.
    """
    st_conj = quaternion_conjugate(dq[:4])
    dual_conj = quaternion_conjugate(dq[4:])
    dual_neg = -dual_conj
    return np.concatenate([st_conj, dual_neg])


def dual_quaternion_norm(dq):
    """Norm squared of a dual quaternion as dual number."""
    # |q|^2 = |q_st|^2 + ε·2·sc(q_st·q_dual*)
    st_sq = dq[0]**2 + dq[1]**2 + dq[2]**2 + dq[3]**2
    st_dual = 2 * (dq[0]*dq[4] + dq[1]*dq[5] + dq[2]*dq[6] + dq[3]*dq[7])
    return st_sq + st_dual * 1e-10  # dual number (epsilon term is tiny)


def normalize_dq(dq):
    """Normalize dual quaternion to unit dual quaternion."""
    st = dq[:4]
    dual = dq[4:]
    norm_st = np.linalg.norm(st)
    if norm_st < 1e-12:
        return np.concatenate([[1.0, 0.0, 0.0, 0.0], dual])
    st_norm = st / norm_st
    # Dual part: subtract projection onto standard part
    # For unit dual quat: sc(q_st_new·q_dual_new*) = 0
    # sc(st_norm·dual*) = st_norm·dual / norm_st
    proj = np.dot(st_norm, dual) / norm_st
    dual_corrected = dual - proj * st_norm
    return np.concatenate([st_norm, dual_corrected])


def dual_quat_mul(a, b):
    """
    Dual quaternion multiplication a · b.
    a, b are 8-element arrays [q_st, q_dual], b is 8-element [q_st, q_dual].
    """
    a_st = a[:4]
    a_dual = a[4:]
    b_st = b[:4]
    b_dual = b[4:]

    # Standard: a_st · b_st
    c_st = quaternion_multiply(a_st, b_st)
    # Dual: a_st · b_dual + a_dual · b_st
    c_dual = quaternion_multiply(a_st, b_dual) + quaternion_multiply(a_dual, b_st)
    return np.concatenate([c_st, c_dual])


def dual_quat_mul_right(a, b):
    """
    Right multiplication: (dual quaternion a) acting on (dual quaternion b) from left.
    Actually: C_ij · x_j where C_ij and x_j are dual quaternions.
    a is C_ij (8 elements), b is x_j (8 elements).
    a · b = a_st·b_st + ε·(a_st·b_dual + a_dual·b_st)
    """
    return dual_quat_mul(a, b)


class MeasurementMatrix:
    """
    Hermitian dual quaternion measurement matrix C = x x* + noise.

    C is n×n with dual quaternion entries. Entry (i,j) is:
      C[i,j] = x_i · x_j* + noise_ij

    The matvec y = C @ x computes:
      y_i = sum_j C[i,j] · x_j

    where · is dual quaternion multiplication.
    """

    def __init__(self, C_entries, neighbors=None):
        """
        C_entries: (n, n, 8) array of dual quaternions.
        C_entries[i, j] = dual quaternion C_ij.
        """
        self.n = C_entries.shape[0]
        self.C = C_entries.copy()
        self.neighbors = neighbors

    def matvec(self, x):
        """
        y = C @ x where x is (n, 8) array of dual quaternions.
        Returns (n, 8) array of dual quaternions.
        """
        n = self.n
        y = np.zeros((n, 8))
        for i in range(n):
            for j in range(n):
                if self.neighbors is not None and j not in self.neighbors.get(i, set()):
                    continue
                y[i] += dual_quat_mul(self.C[i, j], x[j])
        return y

    def dominant_eigenvector_power_iteration(self, max_iter=2000, tol=1e-8):
        """
        Power iteration to find dominant right eigenvector of C.
        Returns eigenvector as (n, 8) array of dual quaternions.
        """
        x = np.zeros((self.n, 8))
        for i in range(self.n):
            dq = sample_random_unit_dual_quaternion()
            x[i, :4] = dq.q_st
            x[i, 4:] = dq.q_dual

        for it in range(max_iter):
            y = self.matvec(x)
            # Normalize: normalize each dual quaternion
            y_norm = np.zeros((self.n, 8))
            for i in range(self.n):
                y_norm[i] = normalize_dq(y[i])
            # Check convergence
            diff = np.max(np.abs(y_norm - x))
            x = y_norm
            if diff < tol:
                break

        return x


def build_measurement_matrix(poses, noise_dict, edge_mask=None):
    """
    Build the Hermitian dual quaternion measurement matrix.

    C_ij = x_i x_j* + ξ_ij
    C_ii = 1 (identity)

    Args:
        poses: list of n DualQuaternion objects (ground truth or initial)
        noise_dict: dict of {(i,j): noise_dual_quaternion} for observed edges
        edge_mask: optional dict of {(i,j): True} for sparse graphs
    """
    n = len(poses)
    C_entries = np.zeros((n, n, 8))

    # Diagonal: C_ii = 1 (identity dual quaternion)
    C_entries[np.arange(n), np.arange(n), 0] = 1.0

    # Off-diagonal entries
    for i in range(n):
        for j in range(i + 1, n):
            if edge_mask is not None:
                if (i, j) not in edge_mask and (j, i) not in edge_mask:
                    continue

            key = (i, j) if (i, j) in noise_dict else (j, i)
            noise = noise_dict.get(key, None)

            # x_i x_j* (dual quaternion product)
            dq_i = np.concatenate([poses[i].q_st, poses[i].q_dual])
            dq_j_conj = np.concatenate([quaternion_conjugate(poses[j].q_st), poses[j].q_dual])
            prod = dual_quat_mul(dq_i, dq_j_conj)

            if noise is not None:
                noise_vec = np.concatenate([noise.q_st, noise.q_dual])
                entry = prod + noise_vec
            else:
                entry = prod

            C_entries[i, j] = entry
            # Hermitian: C_ji = C_ij* (conjugate transpose)
            C_entries[j, i] = dual_quaternion_conjugate(entry)

    return MeasurementMatrix(C_entries)


def dq_to_array(dq):
    """Convert DualQuaternion to 8-element array."""
    if isinstance(dq, np.ndarray):
        return dq
    return np.concatenate([dq.q_st, dq.q_dual])


def project_onto_udq_n(x):
    """
    Project x (n×8 dual quaternion array) onto UDQ^n by normalizing each entry.
    """
    n = x.shape[0]
    result = np.zeros((n, 8))
    for i in range(n):
        result[i] = normalize_dq(x[i])
    return result


def spectral_initializer(C, use_eigh=False, tol=1e-8, max_iter=2000, n_restarts=20):
    """
    Spectral initialization for SE(3) synchronization.
    Uses power iteration to find dominant eigenvector.
    """
    best_result = None
    best_score = -1

    for seed in range(n_restarts):
        np.random.seed(seed)
        x = np.zeros((C.n, 8))
        for i in range(C.n):
            dq = sample_random_unit_dual_quaternion()
            x[i, :4] = dq.q_st
            x[i, 4:] = dq.q_dual

        for _ in range(max_iter):
            y = C.matvec(x)
            y_norm = project_onto_udq_n(y)
            diff = np.max(np.abs(y_norm - x))
            x = y_norm
            if diff < tol:
                break

        # Score: Rayleigh quotient of the result
        Cx = C.matvec(x)
        score = 0.0
        for i in range(C.n):
            inner = 0.0
            for j in range(C.n):
                prod = dual_quat_mul(dual_quaternion_conjugate(x[j]), Cx[i])
                inner += quaternion_inner_product(np.ones(4), prod[:4])
            score += inner
        for i in range(C.n):
            score -= quaternion_inner_product(x[i, :4], x[i, :4])

        if score > best_score:
            best_score = score
            best_result = x.copy()

    return best_result


def dqgpm(C, x0, max_iter=50, tol=1e-8):
    """
    Dual Quaternion Generalized Power Method (DQGPM).
    Algorithm 2 from the paper.

    Refines the spectral initializer by alternating between:
    1. Multiplication by C
    2. Projection onto UDQ^n (element-wise)
    """
    x = x0.copy()

    for k in range(max_iter):
        y = C.matvec(x)
        x_new = project_onto_udq_n(y)
        diff = np.max(np.abs(x_new - x)) / (np.max(np.abs(x)) + 1e-12)
        if diff < tol:
            x = x_new
            break
        x = x_new

    return x


def align_and_compute_errors(est_x, true_poses):
    """
    Align estimated poses to ground truth and compute errors.
    """
    n = len(true_poses)

    # Extract rotations and translations from estimated dual quaternions
    est_rots = []
    est_trans = []
    for i in range(n):
        dq = normalize_dq(est_x[i])
        est_rots.append(dq[:4])
        # t = 2 * vc(q_dual · q_st*)
        t_quat = quaternion_multiply(dq[4:], quaternion_conjugate(dq[:4]))
        est_trans.append(np.array([t_quat[1], t_quat[2], t_quat[3]]))

    # Extract ground truth rotations and translations
    true_rots = []
    true_trans = []
    for p in true_poses:
        true_rots.append(p.q_st)
        t_quat = quaternion_multiply(p.q_dual, quaternion_conjugate(p.q_st))
        true_trans.append(np.array([t_quat[1], t_quat[2], t_quat[3]]))

    # Gauge alignment
    s = np.zeros(4)
    for j in range(n):
        s += quaternion_multiply(quaternion_conjugate(true_rots[j]), est_rots[j])
    q_align = normalize_quaternion(s)

    # Translation alignment
    t_align = np.zeros(3)
    for j in range(n):
        t_est_quat = np.array([0.0, est_trans[j][0], est_trans[j][1], est_trans[j][2]])
        t_rot = quaternion_multiply(
            quaternion_multiply(q_align, t_est_quat),
            quaternion_conjugate(q_align)
        )
        t_rot_vec = np.array([t_rot[1], t_rot[2], t_rot[3]])
        t_align += true_trans[j] - t_rot_vec
    t_align = t_align / n

    # Compute errors
    errors_R = []
    errors_T = []
    for i in range(n):
        q_est = est_rots[i]
        q_aligned = quaternion_multiply(q_align, q_est)
        err_R = rotation_error(q_aligned, true_rots[i])
        errors_R.append(err_R)

        t_est = est_trans[i]
        t_est_quat = np.array([0.0, t_est[0], t_est[1], t_est[2]])
        t_rot = quaternion_multiply(
            quaternion_multiply(q_align, t_est_quat),
            quaternion_conjugate(q_align)
        )
        t_rotated = np.array([t_rot[1], t_rot[2], t_rot[3]]) + t_align
        err_T = translation_error(t_rotated, true_trans[i])
        errors_T.append(err_T)

    return np.mean(errors_R), np.mean(errors_T)


# Aliases for API compatibility
compute_errors_with_alignment = align_and_compute_errors


class DualQuaternionMatrix:
    """Wrapper for evaluation script compatibility."""

    def __init__(self, poses, noise_dict=None, edge_mask=None):
        self.n = len(poses)
        self.poses = poses
        self.noise_dict = noise_dict or {}
        self.edge_mask = edge_mask
        self.measurement = build_measurement_matrix(poses, self.noise_dict, edge_mask)

    def matvec(self, x):
        return self.measurement.matvec(x)

    def dominant_eigenvector(self, method='power_iter'):
        return self.measurement.dominant_eigenvector_power_iteration()

    def dominant_eigenvector_power_iteration(self, max_iter=2000, tol=1e-8):
        return self.measurement.dominant_eigenvector_power_iteration(max_iter=max_iter, tol=tol)
