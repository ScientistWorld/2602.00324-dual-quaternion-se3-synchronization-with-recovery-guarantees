"""Method-independent synthetic SE(3) synchronization benchmark generator."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


EXPERIMENTS = {
    "p005_noise005": (100, 0.05, 0.05, 5.0),
    "p005_noise010": (100, 0.05, 0.10, 10.0),
    "p008_noise010": (100, 0.08, 0.10, 10.0),
    "p030_noise010": (100, 0.30, 0.10, 10.0),
    "p030_noise005": (100, 0.30, 0.05, 5.0),
}


@dataclass(frozen=True)
class BenchmarkInstance:
    experiment: str
    seed: int
    n: int
    p: float
    sigma_t: float
    sigma_r_deg: float
    truth: list[dict]
    measurements: list[dict]


def q_conj(q: np.ndarray) -> np.ndarray:
    return np.array([q[0], -q[1], -q[2], -q[3]], dtype=np.float64)


def q_mul(p: np.ndarray, q: np.ndarray) -> np.ndarray:
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


def q_norm(q: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(q)
    if norm < 1e-14:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    return q / norm


def dq_from_axis_angle_translation(
    axis: np.ndarray, angle: float, translation: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    axis_norm = np.linalg.norm(axis)
    if axis_norm < 1e-14:
        axis = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    else:
        axis = axis / axis_norm
    half = 0.5 * float(angle)
    q_st = q_norm(np.array([np.cos(half), *(np.sin(half) * axis)], dtype=np.float64))
    q_dual = 0.5 * q_mul(np.array([0.0, *translation], dtype=np.float64), q_st)
    return q_st, q_dual


def dq_mul(p: tuple[np.ndarray, np.ndarray], q: tuple[np.ndarray, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    p_st, p_dual = p
    q_st, q_dual = q
    return (
        q_mul(p_st, q_st),
        q_mul(p_st, q_dual) + q_mul(p_dual, q_st),
    )


def dq_conj(x: tuple[np.ndarray, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    return q_conj(x[0]), q_conj(x[1])


def as_record(x: tuple[np.ndarray, np.ndarray]) -> dict:
    return {"q_st": x[0].tolist(), "q_dual": x[1].tolist()}


def sample_pose(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    axis = rng.normal(size=3)
    axis = axis / np.linalg.norm(axis)
    angle = rng.uniform(0.0, 2.0 * np.pi)
    translation = rng.normal(size=3)
    return dq_from_axis_angle_translation(axis, angle, translation)


def sample_noise(
    rng: np.random.Generator, sigma_t: float, sigma_r_deg: float
) -> tuple[np.ndarray, np.ndarray]:
    axis = rng.normal(size=3)
    axis = axis / np.linalg.norm(axis)
    angle = np.deg2rad(rng.normal(loc=0.0, scale=sigma_r_deg))
    translation = rng.normal(loc=0.0, scale=sigma_t, size=3)
    return dq_from_axis_angle_translation(axis, angle, translation)


def generate_instance(experiment: str, seed: int) -> BenchmarkInstance:
    """Generate one fixed-protocol synthetic synchronization instance."""
    if experiment not in EXPERIMENTS:
        raise ValueError(f"unknown experiment: {experiment}")
    n, p, sigma_t, sigma_r_deg = EXPERIMENTS[experiment]
    rng = np.random.default_rng(seed)
    poses = [sample_pose(rng) for _ in range(n)]
    identity = (np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64), np.zeros(4))

    measurements = []
    for i in range(n):
        measurements.append({"i": i, "j": i, **as_record(identity)})
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() > p:
                continue
            relative = dq_mul(poses[i], dq_conj(poses[j]))
            noise = sample_noise(rng, sigma_t, sigma_r_deg)
            noisy = (relative[0] + noise[0] - identity[0], relative[1] + noise[1])
            measurements.append({"i": i, "j": j, **as_record(noisy)})

    return BenchmarkInstance(
        experiment=experiment,
        seed=seed,
        n=n,
        p=p,
        sigma_t=sigma_t,
        sigma_r_deg=sigma_r_deg,
        truth=[as_record(pose) for pose in poses],
        measurements=measurements,
    )
