"""Two-stage DQGPM solver for the paper's SE(3) synchronization problem."""

from __future__ import annotations

import numpy as np

try:
    from .dual_quaternion import (
        DualQuaternion,
        dual_quaternion_multiply,
        normalize_dual_quaternion,
        quaternion_conjugate,
        quaternion_multiply,
        sample_noise_unit_dual_quaternion,
        sample_random_unit_dual_quaternion,
    )
except ImportError:  # pragma: no cover - script execution path
    from dual_quaternion import (
        DualQuaternion,
        dual_quaternion_multiply,
        normalize_dual_quaternion,
        quaternion_conjugate,
        quaternion_multiply,
        sample_noise_unit_dual_quaternion,
        sample_random_unit_dual_quaternion,
    )


def left_mul_matrix(q: np.ndarray) -> np.ndarray:
    w, x, y, z = q
    return np.array(
        [
            [w, -x, -y, -z],
            [x, w, -z, y],
            [y, z, w, -x],
            [z, -y, x, w],
        ],
        dtype=np.float64,
    )


def vector_from_dqs(dqs: list[DualQuaternion]) -> np.ndarray:
    n = len(dqs)
    out = np.zeros(8 * n, dtype=np.float64)
    for i, dq in enumerate(dqs):
        out[4 * i : 4 * i + 4] = dq.q_st
        out[4 * n + 4 * i : 4 * n + 4 * i + 4] = dq.q_dual
    return out


def dqs_from_vector(x: np.ndarray) -> list[DualQuaternion]:
    n = len(x) // 8
    return [
        DualQuaternion(x[4 * i : 4 * i + 4], x[4 * n + 4 * i : 4 * n + 4 * i + 4])
        for i in range(n)
    ]


class MeasurementMatrix:
    """Hermitian dual-quaternion matrix stored as standard and dual parts."""

    def __init__(self, c_st: np.ndarray, c_dual: np.ndarray, neighbors: list[list[int]]):
        self.c_st = np.asarray(c_st, dtype=np.float64)
        self.c_dual = np.asarray(c_dual, dtype=np.float64)
        self.neighbors = neighbors
        self.n = self.c_st.shape[1]

    def matvec(self, x: np.ndarray) -> np.ndarray:
        n = self.n
        y = np.zeros(8 * n, dtype=np.float64)
        for i in range(n):
            st_sum = np.zeros(4, dtype=np.float64)
            dual_sum = np.zeros(4, dtype=np.float64)
            for j in self.neighbors[i]:
                st_j = x[4 * j : 4 * j + 4]
                dual_j = x[4 * n + 4 * j : 4 * n + 4 * j + 4]
                cij_st = self.c_st[:, i, j]
                cij_dual = self.c_dual[:, i, j]
                st_sum += left_mul_matrix(cij_st) @ st_j
                dual_sum += quaternion_multiply(cij_st, dual_j)
                dual_sum += quaternion_multiply(cij_dual, st_j)
            y[4 * i : 4 * i + 4] = st_sum
            y[4 * n + 4 * i : 4 * n + 4 * i + 4] = dual_sum
        return y


def build_synthetic_measurement(
    n: int,
    p: float,
    sigma_t: float,
    sigma_r_deg: float,
    seed: int,
) -> tuple[MeasurementMatrix, list[DualQuaternion], int]:
    """Generate the shifted ER measurement model from Section 4.1."""
    rng = np.random.default_rng(seed)
    poses = [sample_random_unit_dual_quaternion(rng) for _ in range(n)]
    c_st = np.zeros((4, n, n), dtype=np.float64)
    c_dual = np.zeros((4, n, n), dtype=np.float64)
    neighbors = [[] for _ in range(n)]

    for i in range(n):
        c_st[0, i, i] = 1.0
        neighbors[i].append(i)

    identity = DualQuaternion.identity()
    edge_count = 0
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() > p:
                continue
            edge_count += 1
            signal = dual_quaternion_multiply(poses[i], poses[j].conjugate())
            xi = sample_noise_unit_dual_quaternion(sigma_t, sigma_r_deg, rng)
            cij = DualQuaternion(signal.q_st + xi.q_st - identity.q_st, signal.q_dual + xi.q_dual)
            c_st[:, i, j] = cij.q_st
            c_dual[:, i, j] = cij.q_dual
            c_st[:, j, i] = quaternion_conjugate(cij.q_st)
            c_dual[:, j, i] = quaternion_conjugate(cij.q_dual)
            neighbors[i].append(j)
            neighbors[j].append(i)

    return MeasurementMatrix(c_st, c_dual, neighbors), poses, edge_count


def project_onto_udq_n(x: np.ndarray) -> np.ndarray:
    return vector_from_dqs([normalize_dual_quaternion(dq) for dq in dqs_from_vector(x)])


def spectral_power_initializer(
    c: MeasurementMatrix,
    seed: int,
    tol: float = 1e-5,
    max_iter: int = 2000,
) -> tuple[np.ndarray, int, float]:
    """Algorithm 1: power iteration on the dual-quaternion measurement matrix."""
    rng = np.random.default_rng(seed)
    x = rng.normal(size=8 * c.n)
    x /= np.linalg.norm(x[: 4 * c.n])
    residual = np.inf

    for it in range(1, max_iter + 1):
        y = c.matvec(x)
        st_norm = np.linalg.norm(y[: 4 * c.n])
        if st_norm < 1e-14:
            break
        x_next = y / st_norm
        residual = np.linalg.norm(x_next - x) / max(np.linalg.norm(x), 1e-14)
        x = x_next
        if residual < tol:
            break

    # Algorithm 1 outputs sqrt(n) w^k before the GPM stage.
    return np.sqrt(c.n) * x, it, float(residual)


def dqgpm(
    c: MeasurementMatrix,
    x0: np.ndarray,
    max_iter: int = 50,
    tol: float = 1e-8,
    record_history: bool = False,
) -> tuple[np.ndarray, list[np.ndarray]]:
    """Algorithm 2: y=Cx followed by elementwise projection onto UDQ^n."""
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


def run_trial(
    n: int,
    p: float,
    sigma_t: float,
    sigma_r_deg: float,
    seed: int,
    method: str,
    max_iter: int = 50,
) -> dict:
    c, poses, edge_count = build_synthetic_measurement(n, p, sigma_t, sigma_r_deg, seed)
    x0, init_iters, init_residual = spectral_power_initializer(c, seed + 10_000)
    x0_projected = project_onto_udq_n(x0)
    if method == "eig":
        estimate = x0_projected
        history = []
    elif method == "dqgpm":
        estimate, history = dqgpm(c, x0, max_iter=max_iter, record_history=True)
    else:
        raise ValueError(f"unknown method: {method}")

    return {
        "seed": seed,
        "n": n,
        "p": p,
        "sigma_t": sigma_t,
        "sigma_r_deg": sigma_r_deg,
        "edge_count": edge_count,
        "method": method,
        "init_iters": init_iters,
        "init_residual": init_residual,
        "truth": [
            {"q_st": dq.q_st.tolist(), "q_dual": dq.q_dual.tolist()} for dq in poses
        ],
        "estimate": _vector_to_records(estimate),
        "spectral_estimate": _vector_to_records(x0_projected),
        "history": [_vector_to_records(h) for h in history],
    }


def _vector_to_records(x: np.ndarray) -> list[dict]:
    return [
        {"q_st": dq.q_st.tolist(), "q_dual": dq.q_dual.tolist()}
        for dq in dqs_from_vector(project_onto_udq_n(x))
    ]
