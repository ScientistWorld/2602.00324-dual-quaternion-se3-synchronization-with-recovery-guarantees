"""
SE(3) Synchronization via Dual Quaternions.

Implements the two-stage algorithm from:
"Dual Quaternion SE(3) Synchronization with Recovery Guarantees"
Zhao, Zhu, So (2026)

Approach:
- Build the 4n x 4n real matrix representation of the quaternion-Hermitian measurement matrix
- Use power iteration / eigenvalue decomposition to find dominant eigenvector
- Project onto UDQ^n via per-entry dual quaternion normalization
- Run DQGPM for iterative refinement
"""

import numpy as np
from dual_quaternion import (
    quaternion_multiply, quaternion_conjugate, quaternion_inner_product,
    normalize_quaternion, normalize_dual_quaternion, DualQuaternion,
    sample_random_unit_dual_quaternion, sample_random_noise_dual_quaternion,
    rotation_error, translation_error, dual_quaternion_multiply
)


def left_mul_matrix(q):
    """Left multiplication matrix L(q) such that L(q) @ v = q * v"""
    w, x, y, z = q[0], q[1], q[2], q[3]
    return np.array([
        [w, -x, -y, -z],
        [x,  w, -z,  y],
        [y,  z,  w, -x],
        [z, -y,  x,  w]
    ])


class MeasurementMatrix:
    """
    Hermitian dual quaternion measurement matrix C = C_st + C_dual * eps.
    C_st and C_dual are n x n quaternion matrices.
    C_st is quaternion-Hermitian: C_st[j,i] = C_st[i,j]*
    C_dual is quaternion Hermitian: C_dual[j,i] = C_dual[i,j]*

    matvec uses vectorized operations for speed:
    result_st[i] = st_i + sum_j L(C_st[i,j]) @ st_j + sum_j L(C_dual[i,j]) @ st_j + sum_j L(C_st[i,j]) @ dual_j
    result_dual[i] = dual_i + sum_j L(C_dual[i,j]) @ st_j + sum_j L(C_st[i,j]) @ dual_j
    """

    def __init__(self, C_st, C_dual, neighbors=None):
        self.n = C_st.shape[2]
        self.C_st = C_st.copy()
        self.C_dual = C_dual.copy()
        self.neighbors = neighbors
        self.is_sparse = neighbors is not None

        if not self.is_sparse:
            # Dense: precompute (n, 4, 4) stacked left-multiply matrices
            # L_st[i] = sum over j of L(C_st[i,j]) — for each target i
            L_st = np.zeros((self.n, 4, 4))
            L_dual = np.zeros((self.n, 4, 4))
            for i in range(self.n):
                for j in range(self.n):
                    if i == j:
                        L_st[i] += np.eye(4)  # diagonal contribution
                        L_dual[i] += np.zeros((4, 4))  # no dual diag
                    else:
                        L_st[i] += left_mul_matrix(self.C_st[:, i, j])
                        L_dual[i] += left_mul_matrix(self.C_dual[:, i, j])
            self._L_st = L_st  # (n, 4, 4)
            self._L_dual = L_dual  # (n, 4, 4)
        else:
            # Sparse: store (n, max_neighbors, 4, 4) matrices
            max_deg = max(len(nbrs) for nbrs in neighbors.values()) if neighbors else 0
            # Actually, for sparse we use a different approach: store as COO-like
            # For now, fall back to explicit loops
            self._L_st = None
            self._L_dual = None

    def matvec(self, x):
        """Vectorized matvec using precomputed L matrices."""
        n = self.n

        if not self.is_sparse:
            # Dense: explicit loop (clearest, correct implementation)
            result = np.zeros(8 * n)
            for i in range(n):
                st_sum = np.zeros(4)
                dual_sum = np.zeros(4)
                for j in range(n):
                    L_st_ij = left_mul_matrix(self.C_st[:, i, j])
                    # Correct dual quaternion product: C_ij * x_j
                    # (st_ij + dual_ij*eps) * (st_j + dual_j*eps) = st_ij*st_j + (st_ij*dual_j + dual_ij*st_j)*eps
                    # st part: L_st_ij @ st_j ✓
                    st_sum += L_st_ij @ x[4*j:4*j+4]
                    # dual part: st_ij*dual_j + dual_ij*st_j
                    dual_sum += quaternion_multiply(self.C_st[:, i, j], x[4*n + 4*j:4*n + 4*j+4])
                    dual_sum += quaternion_multiply(self.C_dual[:, i, j], x[4*j:4*j+4])
                result[4*i:4*i+4] = st_sum
                result[4*n + 4*i:4*n + 4*i+4] = dual_sum
        else:
            # Sparse: explicit loop
            result = np.zeros(8 * n)
            for i in range(n):
                st_sum = x[4*i:4*i+4].copy()
                dual_sum = x[4*n + 4*i:4*n + 4*i+4].copy()

                for j in self.neighbors.get(i, []):
                    if i == j:
                        continue
                    st_j = x[4*j:4*j+4]
                    dual_j = x[4*n + 4*j:4*n + 4*j+4]
                    L_st = left_mul_matrix(self.C_st[:, i, j])
                    L_dual = left_mul_matrix(self.C_dual[:, i, j])
                    st_sum += L_st @ st_j
                    dual_sum += L_dual @ st_j
                    dual_sum += L_st @ dual_j

                result[4*i:4*i+4] = st_sum
                result[4*n + 4*i:4*n + 4*i+4] = dual_sum

        return result

    def dominant_eigenvector(self, method='power_iter'):
        """Compute dominant eigenvector using power iteration on the matvec."""
        if method == 'power_iter':
            x = np.random.randn(8 * self.n)
            x = x / np.linalg.norm(x)
            for _ in range(1000):
                y = self.matvec(x)
                y_norm = np.linalg.norm(y)
                if y_norm < 1e-12:
                    break
                x_new = y / y_norm
                if np.max(np.abs(x_new - x)) < 1e-8:
                    break
                x = x_new
            if x[0] < 0:
                x = -x
            return x, np.dot(self.matvec(x), x) / np.dot(x, x)
        else:
            raise ValueError(f"Unknown method: {method}")


def build_measurement_matrix(poses, noise_dict, edge_mask=None):
    """
    Build the Hermitian dual quaternion measurement matrix.

    C_ij = x̂_i * x̂_j* + ξ_ij
    For i=j, C_ii = 1.

    In quaternion form:
    C_st[i,j] = st(x̂_i * x̂_j*) + ξ_ij_st
    C_dual[i,j] = dual(x̂_i * x̂_j*) + ξ_ij_dual
    C_st[i,i] = 1, C_dual[i,i] = 0

    The matrix is Hermitian: C_st[j,i] = C_st[i,j]*, C_dual[j,i] = C_dual[i,j]*.
    """
    n = len(poses)

    C_st = np.zeros((4, n, n))
    C_dual = np.zeros((4, n, n))

    # Build neighbor dict if sparse
    neighbors = {} if edge_mask is not None else None
    if neighbors is not None:
        for i in range(n):
            neighbors[i] = []

    # Diagonal
    for i in range(n):
        C_st[0, i, i] = 1.0

    if edge_mask is None:
        for i in range(n):
            for j in range(i+1, n):
                key = (i, j) if (i, j) in noise_dict else (j, i)
                noise = noise_dict.get(key, None)

                xij_conj = dual_quaternion_multiply(poses[i], poses[j].conjugate())
                rel_st = xij_conj.q_st
                rel_dual = xij_conj.q_dual

                if noise is not None:
                    noise_st = noise.q_st
                    noise_dual = noise.q_dual
                else:
                    noise_st = np.array([0.0, 0.0, 0.0, 0.0])
                    noise_dual = np.array([0.0, 0.0, 0.0, 0.0])

                C_st[:, i, j] = rel_st + noise_st
                C_st[:, j, i] = quaternion_conjugate(C_st[:, i, j])

                C_dual[:, i, j] = rel_dual + noise_dual
                C_dual[:, j, i] = quaternion_conjugate(C_dual[:, i, j])
    else:
        for i in range(n):
            for j in range(i+1, n):
                if (i, j) not in edge_mask and (j, i) not in edge_mask:
                    continue

                key = (i, j) if (i, j) in noise_dict else (j, i)
                noise = noise_dict.get(key, None)

                xij_conj = dual_quaternion_multiply(poses[i], poses[j].conjugate())
                rel_st = xij_conj.q_st
                rel_dual = xij_conj.q_dual

                if noise is not None:
                    noise_st = noise.q_st
                    noise_dual = noise.q_dual
                else:
                    noise_st = np.array([0.0, 0.0, 0.0, 0.0])
                    noise_dual = np.array([0.0, 0.0, 0.0, 0.0])

                C_st[:, i, j] = rel_st + noise_st
                C_st[:, j, i] = quaternion_conjugate(C_st[:, i, j])

                C_dual[:, i, j] = rel_dual + noise_dual
                C_dual[:, j, i] = quaternion_conjugate(C_dual[:, i, j])

                if neighbors is not None:
                    neighbors[i].append(j)
                    neighbors[j].append(i)

    return MeasurementMatrix(C_st, C_dual, neighbors)


def project_onto_udq_n_from_real(x_real):
    """
    Project real eigenvector onto UDQ^n.
    x_real is 8n real vector: [st_0...st_{n-1}, dual_0...dual_{n-1}]
    Returns 8n vector where each quaternion pair (st_i, dual_i) is normalized to unit dual quaternion.
    """
    n = len(x_real) // 8
    result = np.zeros(8 * n)

    for i in range(n):
        st = x_real[4*i:4*i+4]
        dual = x_real[4*n + 4*i:4*n + 4*i+4]
        dq = normalize_dual_quaternion(DualQuaternion(st, dual))
        result[4*i:4*i+4] = dq.q_st
        result[4*n + 4*i:4*n + 4*i+4] = dq.q_dual

    return result


def spectral_initializer(C, use_eigh=True, tol=1e-8, max_iter=1000):
    """
    Two-stage spectral initialization using power iteration.
    1. Run power iteration to find dominant eigenvector
    2. Project element-wise onto UDQ^n

    use_eigh=True builds full operator matrix and uses np.linalg.eig (slow but
    finds eigenvalue closest to n). use_eigh=False uses pure power iteration
    (fast but non-deterministic — finds a random eigenvector in eigenspace).
    """
    n = C.n

    if use_eigh:
        # Build operator matrix numerically using matvec
        M_op = np.zeros((8 * n, 8 * n))
        for k in range(8 * n):
            e = np.zeros(8 * n)
            e[k] = 1.0
            M_op[:, k] = C.matvec(e)

        eigvals, eigvecs = np.linalg.eig(M_op)
        eigvals_r = np.real(eigvals)

        target = float(n)
        idx = np.argmin(np.abs(eigvals_r - target))
        v = np.real(eigvecs[:, idx])
        if v[0] < 0:
            v = -v
        x_proj = project_onto_udq_n_from_real(v)
        return x_proj
    else:
        # Power iteration fallback
        x = np.random.randn(8 * n)
        x = x / np.linalg.norm(x)
        for it in range(max_iter):
            y = C.matvec(x)
            y_norm = np.linalg.norm(y)
            if y_norm < 1e-12:
                break
            x_new = y / y_norm
            if np.max(np.abs(x_new - x)) < tol:
                break
            x = x_new
        x_proj = project_onto_udq_n_from_real(x)
        return x_proj


def dqgpm(C, x0, max_iter=50, tol=1e-8):
    """
    Dual Quaternion Generalized Power Method (DQGPM).
    Algorithm 2 from the paper.
    """
    x = x0.copy()

    for k in range(max_iter):
        y = C.matvec(x)
        x_new = project_onto_udq_n_from_real(y)
        diff = np.linalg.norm(x_new - x) / (np.linalg.norm(x) + 1e-12)
        if diff < tol:
            x = x_new
            break
        x = x_new

    return x


def align_and_compute_errors(est_x, true_poses):
    """
    Compute rotation and translation errors after gauge alignment.

    The estimated poses are first normalized to unit dual quaternions.
    Translation is extracted using t = 2 * (q_dual * q_st*).
    Gauge alignment finds optimal global rotation and translation.
    """
    n = len(true_poses)

    # Normalize estimated poses and extract rotation/translation
    est_rots = []
    est_trans = []
    for i in range(n):
        dq = normalize_dual_quaternion(DualQuaternion(
            est_x[4*i:4*i+4],
            est_x[4*n + 4*i:4*n + 4*i+4]
        ))
        est_rots.append(dq.q_st)
        # t = 2 * (q_dual * q_st*) — quaternion product, take vector part
        t_quat = quaternion_multiply(dq.q_dual, quaternion_conjugate(dq.q_st))
        est_trans.append(np.array([t_quat[1], t_quat[2], t_quat[3]]))

    # True rotations and translations
    true_rots = [p.q_st for p in true_poses]
    true_trans = []
    for p in true_poses:
        t_quat = quaternion_multiply(p.q_dual, quaternion_conjugate(p.q_st))
        true_trans.append(np.array([t_quat[1], t_quat[2], t_quat[3]]))

    # Gauge alignment: find optimal q (rotation) aligning est to true
    s = np.zeros(4)
    for j in range(n):
        s += quaternion_multiply(
            quaternion_conjugate(true_rots[j]),
            est_rots[j]
        )
    q_align = normalize_quaternion(s)

    # Translation alignment
    t_align = np.zeros(3)
    for j in range(n):
        q_true = true_rots[j]
        q_est = est_rots[j]
        t_true = true_trans[j]
        t_est = est_trans[j]

        t_est_quat = np.array([0.0, t_est[0], t_est[1], t_est[2]])
        t_rot = quaternion_multiply(
            quaternion_multiply(q_align, t_est_quat),
            quaternion_conjugate(q_align)
        )
        t_rot_vec = np.array([t_rot[1], t_rot[2], t_rot[3]])
        t_align += t_true - t_rot_vec
    t_align = t_align / n

    # Compute errors with alignment
    errors_R = []
    errors_T = []
    for i in range(n):
        q_est = est_rots[i]
        q_aligned = quaternion_multiply(q_align, q_est)
        q_true = true_rots[i]
        err_R = rotation_error(q_aligned, q_true)
        errors_R.append(err_R)

        t_est = est_trans[i]
        t_est_quat = np.array([0.0, t_est[0], t_est[1], t_est[2]])
        t_rot = quaternion_multiply(
            quaternion_multiply(q_align, t_est_quat),
            quaternion_conjugate(q_align)
        )
        t_rotated = np.array([t_rot[1], t_rot[2], t_rot[3]]) + t_align
        t_true = true_trans[i]
        err_T = translation_error(t_rotated, t_true)
        errors_T.append(err_T)

    return np.mean(errors_R), np.mean(errors_T)


# Wrapper aliases for evaluation script compatibility
compute_errors_with_alignment = align_and_compute_errors
project_onto_udq_n = project_onto_udq_n_from_real


class DualQuaternionMatrix:
    """
    Wrapper around MeasurementMatrix for evaluation script compatibility.
    Stores poses, measurement matrix, and provides matvec access.
    """

    def __init__(self, poses, noise_dict=None, edge_mask=None):
        self.n = len(poses)
        self.poses = poses
        self.noise_dict = noise_dict or {}
        self.edge_mask = edge_mask
        self.measurement = build_measurement_matrix(poses, self.noise_dict, edge_mask)

    def matvec(self, x):
        return self.measurement.matvec(x)

    def dominant_eigenvector(self, method='power_iter'):
        return self.measurement.dominant_eigenvector(method)