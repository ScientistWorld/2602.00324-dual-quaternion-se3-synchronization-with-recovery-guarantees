"""Method-independent synthetic SE(3) synchronization benchmark generator.

This is the public (train) side of the benchmark: the generator, the fixed
experiment settings, and the visible trial-seed family.  The hidden test draws
its instances from the same distribution with seeds that only ``eval/test/``
holds.

Command line (writes a measurement-only solver input and, separately, truth):

    python3 -m data.synthetic --experiment p005_noise005 --trials 100 \
        --inputs tmp/p005_noise005_inputs.json --truth tmp/p005_noise005_truth.json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


# (n, p, sigma_t, sigma_r_deg) for the synthetic settings of Table 2.
EXPERIMENTS = {
    "p005_noise005": (100, 0.05, 0.05, 5.0),
    "p005_noise010": (100, 0.05, 0.10, 10.0),
    "p008_noise010": (100, 0.08, 0.10, 10.0),
    "p030_noise010": (100, 0.30, 0.10, 10.0),
    "p030_noise005": (100, 0.30, 0.05, 5.0),
}

# Visible train family: the original 100-trial protocol seeds.
TRAIN_SEED_BASE = 260200324
TRAIN_SEED_STRIDE = 7919
TRAIN_TRIALS = 100
INPUT_FORMAT = "se3-sync-measurements/v1"


def train_seeds(trials: int = TRAIN_TRIALS) -> list[int]:
    return [TRAIN_SEED_BASE + TRAIN_SEED_STRIDE * k for k in range(trials)]


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


def solver_record(instance: BenchmarkInstance, instance_id: str) -> dict:
    """Measurement-only record for one instance (no truth, no seed).

    Only observed off-diagonal pairs i < j are listed; C_ii = 1 and
    C_ji = C_ij^* are implied by the measurement model.
    """
    edges, q_st, q_dual = [], [], []
    for m in instance.measurements:
        if m["i"] == m["j"]:
            continue
        edges.append([m["i"], m["j"]])
        q_st.append(m["q_st"])
        q_dual.append(m["q_dual"])
    return {"id": instance_id, "n": instance.n, "edges": edges, "q_st": q_st, "q_dual": q_dual}


def setting(experiment: str) -> dict:
    n, p, sigma_t, sigma_r_deg = EXPERIMENTS[experiment]
    return {"n": n, "p": p, "sigma_t": sigma_t, "sigma_r_deg": sigma_r_deg}


def train_instances(experiment: str, trials: int = TRAIN_TRIALS) -> list[tuple[str, BenchmarkInstance]]:
    return [
        (f"t{k:03d}", generate_instance(experiment, seed))
        for k, seed in enumerate(train_seeds(trials))
    ]


def solver_input(experiment: str, labelled: list[tuple[str, BenchmarkInstance]]) -> dict:
    return {
        "format": INPUT_FORMAT,
        "experiment": experiment,
        "setting": setting(experiment),
        "instances": [solver_record(inst, inst_id) for inst_id, inst in labelled],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--experiment", required=True, choices=sorted(EXPERIMENTS))
    parser.add_argument("--trials", type=int, default=TRAIN_TRIALS)
    parser.add_argument("--inputs", required=True, help="measurement-only solver input JSON")
    parser.add_argument("--truth", help="optional ground-truth JSON (train family only)")
    args = parser.parse_args()

    labelled = train_instances(args.experiment, args.trials)
    out = Path(args.inputs)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(solver_input(args.experiment, labelled)))
    if args.truth:
        truth = {inst_id: {"seed": inst.seed, "truth": inst.truth} for inst_id, inst in labelled}
        Path(args.truth).parent.mkdir(parents=True, exist_ok=True)
        Path(args.truth).write_text(json.dumps(truth))


if __name__ == "__main__":
    main()
