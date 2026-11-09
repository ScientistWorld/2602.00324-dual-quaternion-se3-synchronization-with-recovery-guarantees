"""Frozen evaluator comparators; only measurement records are accepted.
EIG rounding: https://fusiello.github.io/papers/siims16.pdf, sections 2.2-2.3.
Reference snapshot implements Algorithms 1 and 2 of the reproduced paper.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
def quaternion_conjugate(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, dtype=np.float64)
    return np.array([q[0], -q[1], -q[2], -q[3]], dtype=np.float64)


def quaternion_multiply(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    p = np.asarray(p, dtype=np.float64)
    q = np.asarray(q, dtype=np.float64)
    w1, x1, y1, z1 = p
    w2, x2, y2, z2 = q
    return np.array(
        [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ],
        dtype=np.float64,
    )


def quaternion_inner_product(p: np.ndarray, q: np.ndarray) -> float:
    return float(np.dot(p, q))


def normalize_quaternion(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, dtype=np.float64)
    norm = np.linalg.norm(q)
    if norm < 1e-14:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    return q / norm


def rotate_vector(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    q = normalize_quaternion(q)
    pure = np.array([0.0, v[0], v[1], v[2]], dtype=np.float64)
    out = quaternion_multiply(quaternion_multiply(q, pure), quaternion_conjugate(q))
    return out[1:4]


@dataclass
class DualQuaternion:
    """Dual quaternion q_st + eps q_dual."""

    q_st: np.ndarray
    q_dual: np.ndarray

    def __post_init__(self) -> None:
        self.q_st = np.asarray(self.q_st, dtype=np.float64)
        self.q_dual = np.asarray(self.q_dual, dtype=np.float64)

    @staticmethod
    def identity() -> "DualQuaternion":
        return DualQuaternion(np.array([1.0, 0.0, 0.0, 0.0]), np.zeros(4))

    @staticmethod
    def from_rotation_translation(
        axis: np.ndarray, angle: float, translation: np.ndarray
    ) -> "DualQuaternion":
        axis = np.asarray(axis, dtype=np.float64)
        axis_norm = np.linalg.norm(axis)
        if axis_norm < 1e-14:
            axis = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        else:
            axis = axis / axis_norm

        half = 0.5 * float(angle)
        q = normalize_quaternion(
            np.array(
                [np.cos(half), *(np.sin(half) * axis)],
                dtype=np.float64,
            )
        )
        t_quat = np.array([0.0, *np.asarray(translation, dtype=np.float64)])
        q_dual = 0.5 * quaternion_multiply(t_quat, q)
        return DualQuaternion(q, q_dual)

    def conjugate(self) -> "DualQuaternion":
        return DualQuaternion(
            quaternion_conjugate(self.q_st), quaternion_conjugate(self.q_dual)
        )

    def translation(self) -> np.ndarray:
        t_quat = 2.0 * quaternion_multiply(self.q_dual, quaternion_conjugate(self.q_st))
        return t_quat[1:4]

    def normalized(self) -> "DualQuaternion":
        return normalize_dual_quaternion(self)


def dual_quaternion_multiply(p: DualQuaternion, q: DualQuaternion) -> DualQuaternion:
    st = quaternion_multiply(p.q_st, q.q_st)
    dual = quaternion_multiply(p.q_st, q.q_dual) + quaternion_multiply(p.q_dual, q.q_st)
    return DualQuaternion(st, dual)


def dual_quaternion_add(p: DualQuaternion, q: DualQuaternion) -> DualQuaternion:
    return DualQuaternion(p.q_st + q.q_st, p.q_dual + q.q_dual)


def dual_quaternion_sub(p: DualQuaternion, q: DualQuaternion) -> DualQuaternion:
    return DualQuaternion(p.q_st - q.q_st, p.q_dual - q.q_dual)


def normalize_dual_quaternion(dq: DualQuaternion) -> DualQuaternion:
    """Projection/normalization map N from Proposition 2.7."""
    st = np.asarray(dq.q_st, dtype=np.float64)
    dual = np.asarray(dq.q_dual, dtype=np.float64)
    st_norm_sq = float(np.dot(st, st))

    if st_norm_sq > 1e-14:
        st_norm = np.sqrt(st_norm_sq)
        u_st = st / st_norm
        # Remove the component violating sc(u_st* u_dual)=0.
        u_dual = dual / st_norm
        u_dual = u_dual - np.dot(u_st, u_dual) * u_st
        return DualQuaternion(u_st, u_dual)

    dual_norm = np.linalg.norm(dual)
    if dual_norm > 1e-14:
        u_st = dual / dual_norm
        trial = np.array([0.0, 1.0, 0.0, 0.0])
        if abs(np.dot(trial, u_st)) > 0.9:
            trial = np.array([0.0, 0.0, 1.0, 0.0])
        u_dual = normalize_quaternion(trial - np.dot(trial, u_st) * u_st)
        return DualQuaternion(u_st, u_dual)

    return DualQuaternion.identity()



_CONJ = np.array([1.0, -1.0, -1.0, -1.0])


def left_mul_matrices(q: np.ndarray) -> np.ndarray:
    """Real 4x4 matrices L(q) with L(q) p = q * p, broadcast over leading axes."""
    q = np.asarray(q, dtype=np.float64)
    w, x, y, z = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    return np.stack(
        [
            np.stack([w, -x, -y, -z], axis=-1),
            np.stack([x, w, -z, y], axis=-1),
            np.stack([y, z, w, -x], axis=-1),
            np.stack([z, -y, x, w], axis=-1),
        ],
        axis=-2,
    )


def left_mul_matrix(q: np.ndarray) -> np.ndarray:
    return left_mul_matrices(np.asarray(q, dtype=np.float64).reshape(4))


def vector_from_arrays(st: np.ndarray, dual: np.ndarray) -> np.ndarray:
    return np.concatenate((np.asarray(st, float).reshape(-1), np.asarray(dual, float).reshape(-1)))


def arrays_from_vector(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = len(x) // 8
    return x[: 4 * n].reshape(n, 4), x[4 * n :].reshape(n, 4)


def center_translation_gauge(st: np.ndarray, dual: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Choose the zero-mean body-translation representative of the same poses.

    Right multiplication by one unit translation changes no x_i x_j^*.
    Power iteration leaves this noncompact gauge arbitrary. Serialize it at
    a fixed origin so rotation error does not amplify an arbitrary origin in
    the paper's subsequent translation alignment. Neither iterate is changed.
    """
    st = np.asarray(st, dtype=float)
    dual = np.asarray(dual, dtype=float)
    body = np.array([quaternion_multiply(q * _CONJ, d) for q, d in zip(st, dual)])
    shift = np.r_[0., 2. * body[:, 1:].mean(axis=0)]
    centered = dual - .5 * np.array([quaternion_multiply(q, shift) for q in st])
    return st.copy(), centered


class MeasurementMatrix:
    """Hermitian measurement matrix C with C_ii = 1 and C_ji = C_ij^*."""

    def __init__(self, n: int, edges, c_st, c_dual):
        n = int(n)
        edges = np.asarray(edges, dtype=np.int64).reshape(-1, 2)
        c_st = np.asarray(c_st, dtype=np.float64).reshape(-1, 4)
        c_dual = np.asarray(c_dual, dtype=np.float64).reshape(-1, 4)
        if len(edges) != len(c_st) or len(edges) != len(c_dual):
            raise ValueError("edges, q_st and q_dual must have the same length")
        self.n = n
        self.edges = edges
        self.l_st = np.zeros((4 * n, 4 * n), dtype=np.float64)
        self.l_dual = np.zeros((4 * n, 4 * n), dtype=np.float64)
        eye = np.eye(4)
        for i in range(n):
            self.l_st[4 * i : 4 * i + 4, 4 * i : 4 * i + 4] = eye
        if len(edges):
            l_st = left_mul_matrices(c_st)
            l_dual = left_mul_matrices(c_dual)
            l_st_conj = left_mul_matrices(c_st * _CONJ)
            l_dual_conj = left_mul_matrices(c_dual * _CONJ)
            for k, (i, j) in enumerate(edges):
                if i == j:
                    raise ValueError("diagonal entries are fixed to the identity")
                self.l_st[4 * i : 4 * i + 4, 4 * j : 4 * j + 4] = l_st[k]
                self.l_dual[4 * i : 4 * i + 4, 4 * j : 4 * j + 4] = l_dual[k]
                self.l_st[4 * j : 4 * j + 4, 4 * i : 4 * i + 4] = l_st_conj[k]
                self.l_dual[4 * j : 4 * j + 4, 4 * i : 4 * i + 4] = l_dual_conj[k]

    @classmethod
    def from_instance(cls, instance: dict) -> "MeasurementMatrix":
        return cls(instance["n"], instance["edges"], instance["q_st"], instance["q_dual"])

    def matvec(self, x: np.ndarray) -> np.ndarray:
        n4 = 4 * self.n
        st = x[:n4]
        dual = x[n4:]
        return np.concatenate((self.l_st @ st, self.l_st @ dual + self.l_dual @ st))


def project_onto_udq_n(x: np.ndarray) -> np.ndarray:
    """Elementwise projection onto UDQ^n (Proposition 2.7).

    Nonzero entries are normalized by N(.).  Exact zero entries of a nonzero
    vector use the normalized first nonzero entry (a coordinate vector e with
    e*y != 0).  The all-zero vector maps to the all-identity point.
    """
    st, dual = arrays_from_vector(np.asarray(x, dtype=np.float64))
    n = len(st)
    st_sq = np.einsum("ij,ij->i", st, st)
    dual_sq = np.einsum("ij,ij->i", dual, dual)
    zero = (st_sq < 1e-28) & (dual_sq < 1e-28)
    regular = st_sq > 1e-14

    out_st = np.empty_like(st)
    out_dual = np.empty_like(dual)
    if regular.any():
        norm = np.sqrt(st_sq[regular])[:, None]
        u_st = st[regular] / norm
        u_dual = dual[regular] / norm
        u_dual = u_dual - np.einsum("ij,ij->i", u_st, u_dual)[:, None] * u_st
        out_st[regular] = u_st
        out_dual[regular] = u_dual
    # Rare branches (tiny but nonzero standard part) use the scalar map N(.).
    for i in np.flatnonzero(~zero & ~regular):
        dq = normalize_dual_quaternion(DualQuaternion(st[i], dual[i]))
        out_st[i] = dq.q_st
        out_dual[i] = dq.q_dual
    if zero.any():
        nonzero = np.flatnonzero(~zero)
        if len(nonzero):
            first = nonzero[0]
            fallback_st, fallback_dual = out_st[first].copy(), out_dual[first].copy()
        else:
            fallback_st, fallback_dual = np.array([1.0, 0.0, 0.0, 0.0]), np.zeros(4)
        out_st[zero] = fallback_st
        out_dual[zero] = fallback_dual
    assert out_st.shape == (n, 4)
    return vector_from_arrays(out_st, out_dual)


def _dual_vector_norm(x: np.ndarray) -> tuple[float, float]:
    """Standard and dual parts of the dual-number norm ||x||_2 of a DQ vector."""
    n = len(x) // 8
    st = x[: 4 * n]
    dual = x[4 * n :]
    norm_sq_st = float(np.dot(st, st))
    if norm_sq_st < 1e-28:
        return 0.0, 0.0
    norm_st = float(np.sqrt(norm_sq_st))
    norm_dual = float(np.dot(st, dual) / norm_st)
    return norm_st, norm_dual


def _right_scale_by_dual_scalar(x: np.ndarray, standard: float, dual: float) -> np.ndarray:
    """Right-multiply each vector entry by a real dual number standard + eps dual."""
    n = len(x) // 8
    out = np.empty_like(x)
    out[: 4 * n] = standard * x[: 4 * n]
    out[4 * n :] = standard * x[4 * n :] + dual * x[: 4 * n]
    return out


def normalize_dq_vector(x: np.ndarray) -> np.ndarray:
    """x (||x||_2)^{-1} with the dual-number inverse a^{-1} = a_st^{-1}(1 - a_I a_st^{-1} eps)."""
    norm_st, norm_dual = _dual_vector_norm(x)
    if norm_st < 1e-14:
        return x.copy()
    inv_st = 1.0 / norm_st
    inv_dual = -norm_dual / (norm_st * norm_st)
    return _right_scale_by_dual_scalar(x, inv_st, inv_dual)


def spectral_power_initializer(
    c: MeasurementMatrix,
    seed: int,
    tol: float = 1e-5,
    max_iter: int = 2000,
) -> tuple[np.ndarray, int, float]:
    """Algorithm 1: power iteration on the dual-quaternion measurement matrix.

    Runs until the relative residual ||w^k - w^{k-1}|| / ||w^{k-1}|| drops below
    ``tol`` (Section 4.2 uses 1e-5) or ``max_iter`` iterations, and returns
    sqrt(n) w^k together with the iteration count and final residual.
    """
    rng = np.random.default_rng(seed)
    x = rng.normal(size=8 * c.n)
    x = normalize_dq_vector(x)
    residual = np.inf
    it = 0
    for it in range(1, max_iter + 1):
        y = c.matvec(x)
        y_norm_st, _ = _dual_vector_norm(y)
        if y_norm_st < 1e-14:
            break
        x_next = normalize_dq_vector(y)
        residual = np.linalg.norm(x_next - x) / max(np.linalg.norm(x), 1e-14)
        x = x_next
        if residual < tol:
            break
    return np.sqrt(c.n) * x, it, float(residual)


def dqgpm(
    c: MeasurementMatrix,
    x0: np.ndarray,
    max_iter: int = 200,
    tol: float = 1e-8,
    record_history: bool = False,
) -> tuple[np.ndarray, list[np.ndarray]]:
    """Algorithm 2: x^k = Pi(C x^{k-1}), starting from the unprojected u_1."""
    x = x0.copy()
    history: list[np.ndarray] = []
    for _ in range(max_iter):
        x_next = project_onto_udq_n(c.matvec(x))
        if record_history:
            history.append(x_next.copy())
        diff = np.linalg.norm(x_next - project_onto_udq_n(x)) / np.sqrt(c.n)
        x = x_next
        if diff < tol:
            break
    return x, history


def solve_instance(
    instance: dict,
    seed: int,
    stage: str = "dqgpm",
    init_tol: float = 1e-5,
    init_max_iter: int = 2000,
    gpm_tol: float = 1e-8,
    gpm_max_iter: int = 200,
) -> tuple[np.ndarray, np.ndarray]:
    """Run the two-stage pipeline on one measurement record; return (q_st, q_dual)."""
    c = MeasurementMatrix.from_instance(instance)
    x0, _, _ = spectral_power_initializer(c, seed, tol=init_tol, max_iter=init_max_iter)
    if stage == "spectral":
        estimate = project_onto_udq_n(x0)
    elif stage == "dqgpm":
        estimate, _ = dqgpm(c, x0, max_iter=gpm_max_iter, tol=gpm_tol)
        estimate = project_onto_udq_n(estimate)
    else:
        raise ValueError(f"unknown stage: {stage}")
    return center_translation_gauge(*arrays_from_vector(estimate))

CONJ = np.array([1., -1., -1., -1.])
IDENTITY = np.array([1., 0., 0., 0.])

def qmul(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Hamilton product, broadcast over leading axes (scalar-first)."""
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


def rotmat_from_quat(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, dtype=np.float64)
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


def quat_from_rotmat(r: np.ndarray) -> np.ndarray:
    """Shepperd's method for a stack of rotation matrices (n, 3, 3) -> (n, 4)."""
    r = np.asarray(r, dtype=np.float64)
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


def dq_from_rotation_translation(q: np.ndarray, t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """x = (1 + eps t/2) q  ->  (q, 0.5 * (0, t) q)."""
    t_quat = np.concatenate((np.zeros(t.shape[:-1] + (1,)), t), axis=-1)
    return q, 0.5 * qmul(t_quat, q)


def normalize_rows(c_st: np.ndarray, c_dual: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Normalization N(.) of each dual quaternion (degenerate rows -> identity)."""
    st_sq = np.einsum("ij,ij->i", c_st, c_st)
    ok = st_sq > 1e-14
    norm = np.sqrt(np.where(ok, st_sq, 1.0))[:, None]
    st = np.where(ok[:, None], c_st / norm, IDENTITY)
    dual = np.where(ok[:, None], c_dual / norm, 0.0)
    dual = dual - np.einsum("ij,ij->i", st, dual)[:, None] * st
    return st, dual


def instance_arrays(instance: dict) -> tuple[int, np.ndarray, np.ndarray, np.ndarray]:
    n = int(instance["n"])
    edges = np.asarray(instance["edges"], dtype=np.int64).reshape(-1, 2)
    c_st = np.asarray(instance["q_st"], dtype=np.float64).reshape(-1, 4)
    c_dual = np.asarray(instance["q_dual"], dtype=np.float64).reshape(-1, 4)
    return n, edges, c_st, c_dual



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


def matrix_eig(instance: dict, seed: int = 0):
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
    return center_translation_gauge(*dq_from_rotation_translation(q, t))

def reference(instance, seed=0):
    return solve_instance(instance, seed=seed)

def dq_spectral(instance, seed=0):
    return solve_instance(instance, seed=seed, stage="spectral")

COMPARATORS = {"dq_spectral": dq_spectral, "matrix_eig": matrix_eig}
