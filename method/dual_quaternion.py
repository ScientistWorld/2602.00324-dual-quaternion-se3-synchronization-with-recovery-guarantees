"""Dual quaternion primitives for SE(3) synchronization.

The paper represents an SE(3) pose as x = (1 + eps * t / 2) q, where q is a
unit rotation quaternion and t is a pure translation quaternion.  This module
keeps the standard and dual quaternion components explicit.
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


def sample_random_unit_dual_quaternion(rng: np.random.Generator | None = None) -> DualQuaternion:
    rng = np.random.default_rng() if rng is None else rng
    axis = rng.normal(size=3)
    axis = axis / np.linalg.norm(axis)
    angle = rng.uniform(0.0, 2.0 * np.pi)
    translation = rng.normal(size=3)
    return DualQuaternion.from_rotation_translation(axis, angle, translation)


def sample_noise_unit_dual_quaternion(
    sigma_t: float, sigma_r_deg: float, rng: np.random.Generator | None = None
) -> DualQuaternion:
    rng = np.random.default_rng() if rng is None else rng
    axis = rng.normal(size=3)
    axis = axis / np.linalg.norm(axis)
    angle = np.deg2rad(rng.normal(loc=0.0, scale=sigma_r_deg))
    translation = rng.normal(loc=0.0, scale=sigma_t, size=3)
    return DualQuaternion.from_rotation_translation(axis, angle, translation)


def rotation_error(q1: np.ndarray, q2: np.ndarray) -> float:
    q1 = normalize_quaternion(q1)
    q2 = normalize_quaternion(q2)
    inner = abs(quaternion_inner_product(q1, q2))
    inner = float(np.clip(inner, 0.0, 1.0))
    return float(2.0 * np.arccos(np.clip(2.0 * inner * inner - 1.0, -1.0, 1.0)))


def translation_error(t1: np.ndarray, t2: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(t1) - np.asarray(t2)))
