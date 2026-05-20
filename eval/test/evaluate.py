#!/usr/bin/env python3
"""Held-out test-slice scorer for SE(3) synchronization artifacts.

This evaluator reads method result artifacts only. It does not import or run
method code, and it scores the odd-indexed half of each artifact's trials
after sorting by trial seed. Ground truth poses are reconstructed from each
trial seed instead of trusted from the artifact.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


SLICE = "test"


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
    n = np.linalg.norm(q)
    if n < 1e-14:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    return q / n


def rotate(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    pure = np.array([0.0, v[0], v[1], v[2]])
    return q_mul(q_mul(q_norm(q), pure), q_conj(q_norm(q)))[1:4]


def dual_quaternion_from_rt(axis: np.ndarray, angle: float, translation: np.ndarray) -> dict:
    axis_norm = np.linalg.norm(axis)
    if axis_norm < 1e-14:
        axis = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    else:
        axis = axis / axis_norm

    half = 0.5 * float(angle)
    q_st = q_norm(np.array([np.cos(half), *(np.sin(half) * axis)], dtype=np.float64))
    t_quat = np.array([0.0, *np.asarray(translation, dtype=np.float64)])
    q_dual = 0.5 * q_mul(t_quat, q_st)
    return {"q_st": q_st.tolist(), "q_dual": q_dual.tolist()}


def deterministic_truth(trial: dict, artifact: dict) -> list[dict]:
    """Regenerate the seeded synthetic poses without trusting artifact truth."""
    n = int(trial.get("n", artifact.get("n", 0)))
    if n <= 0:
        raise ValueError("trial artifact must include a positive n")

    rng = np.random.default_rng(int(trial["seed"]))
    poses = []
    for _ in range(n):
        axis = rng.normal(size=3)
        axis = axis / np.linalg.norm(axis)
        angle = rng.uniform(0.0, 2.0 * np.pi)
        translation = rng.normal(size=3)
        poses.append(dual_quaternion_from_rt(axis, angle, translation))
    return poses


def record_pose(record: dict) -> tuple[np.ndarray, np.ndarray]:
    q_st = q_norm(np.asarray(record["q_st"], dtype=np.float64))
    q_dual = np.asarray(record["q_dual"], dtype=np.float64)
    t = 2.0 * q_mul(q_dual, q_conj(q_st))[1:4]
    return q_st, t


def rotation_error(q1: np.ndarray, q2: np.ndarray) -> float:
    inner = abs(float(np.dot(q_norm(q1), q_norm(q2))))
    inner = np.clip(inner, 0.0, 1.0)
    return float(2.0 * np.arccos(np.clip(2.0 * inner * inner - 1.0, -1.0, 1.0)))


def aligned_errors(truth: list[dict], estimate: list[dict]) -> tuple[float, float]:
    true_q, true_t, est_q, est_t = [], [], [], []
    for tr, est in zip(truth, estimate, strict=True):
        q_t, t_t = record_pose(tr)
        q_e, t_e = record_pose(est)
        true_q.append(q_t)
        true_t.append(t_t)
        est_q.append(q_e)
        est_t.append(t_e)

    # Right gauge alignment used by the original evaluator.
    s = np.zeros(4)
    for q_hat, q in zip(true_q, est_q, strict=True):
        s += q_mul(q_conj(q_hat), q)
    q_align = q_norm(s)
    t_align = np.zeros(3)
    for q_hat, t_hat, t in zip(true_q, true_t, est_t, strict=True):
        t_align += rotate(q_conj(q_hat), t - t_hat)
    t_align /= len(truth)

    err_r, err_t = [], []
    for q_hat, t_hat, q, t in zip(true_q, true_t, est_q, est_t, strict=True):
        q_right = q_mul(q_hat, q_align)
        t_right = t_hat + rotate(q_hat, t_align)
        err_r.append(rotation_error(q, q_right))
        err_t.append(float(np.linalg.norm(t - t_right)))
    return float(np.mean(err_r)), float(np.mean(err_t))


def select_trials(trials: list[dict]) -> list[dict]:
    ordered = sorted(enumerate(trials), key=lambda item: (item[1].get("seed", item[0]), item[0]))
    selected = [trial for pos, (_, trial) in enumerate(ordered) if pos % 2 == 1]
    if not selected:
        raise ValueError("test slice has no trials to score")
    return selected


def evaluate_artifact(path: Path) -> dict:
    artifact = json.loads(path.read_text())
    err_r, err_t = [], []
    for trial in select_trials(artifact["trials"]):
        r, t = aligned_errors(deterministic_truth(trial, artifact), trial["estimate"])
        err_r.append(r)
        err_t.append(t)

    return {
        "experiment": artifact["experiment"],
        "method": artifact["method"],
        "error_R": float(np.mean(err_r)),
        "error_R_std": float(np.std(err_r)),
        "error_R_p90": float(np.percentile(err_r, 90)),
        "error_R_max": float(np.max(err_r)),
        "error_T": float(np.mean(err_t)),
        "error_T_std": float(np.std(err_t)),
        "error_T_p90": float(np.percentile(err_t, 90)),
        "error_T_max": float(np.max(err_t)),
    }


def reference_experiments(path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text())
    return set(data.get("experiments", {}))


def expected_entries(train_scores_path: Path) -> set[tuple[str, str]]:
    if not train_scores_path.exists():
        return set()
    data = json.loads(train_scores_path.read_text())
    experiments = data.get("experiments", data)
    entries: set[tuple[str, str]] = set()
    for exp_name, exp_data in experiments.items():
        if exp_name.startswith("_") or not isinstance(exp_data, dict):
            continue
        methods = exp_data.get("results", exp_data)
        if not isinstance(methods, dict):
            continue
        for method_name in methods:
            if not method_name.startswith("_"):
                entries.add((exp_name, method_name))
    return entries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", nargs="+", required=True)
    parser.add_argument("--output", default="scoring/scores_test.json")
    parser.add_argument("--train-scores", default="scoring/scores_train.json")
    parser.add_argument("--reference", default="scoring/reference.json")
    args = parser.parse_args()

    allowed_experiments = reference_experiments(Path(args.reference))
    expected = expected_entries(Path(args.train_scores))
    seen: set[tuple[str, str]] = set()
    by_exp: dict[str, dict] = {}
    for artifact_path in args.artifacts:
        result = evaluate_artifact(Path(artifact_path))
        exp_name = result.pop("experiment")
        if allowed_experiments and exp_name not in allowed_experiments:
            continue
        method = result.pop("method")
        entry = (exp_name, method)
        if expected and entry not in expected:
            continue
        seen.add(entry)
        by_exp.setdefault(
            exp_name,
            {
                "slice": SLICE,
                "trial_selector": "sorted_by_seed_odd_positions",
                "results": {},
            },
        )
        by_exp[exp_name]["results"][method] = result

    missing = sorted(expected - seen)
    if missing:
        formatted = ", ".join(f"{exp}/{method}" for exp, method in missing)
        raise SystemExit(f"Missing test artifacts for train-scored entries: {formatted}")

    payload = {"_metadata": {"slice": SLICE}, "experiments": by_exp}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
