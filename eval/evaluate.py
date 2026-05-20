#!/usr/bin/env python3
"""Evaluate SE(3) synchronization artifacts without importing method code."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

Vector = list[float]


def q_conj(q: Vector) -> Vector:
    return [q[0], -q[1], -q[2], -q[3]]


def q_mul(p: Vector, q: Vector) -> Vector:
    w1, x1, y1, z1 = p
    w2, x2, y2, z2 = q
    return [
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ]


def dot(p: Vector, q: Vector) -> float:
    return sum(a * b for a, b in zip(p, q, strict=True))


def add(p: Vector, q: Vector) -> Vector:
    return [a + b for a, b in zip(p, q, strict=True)]


def sub(p: Vector, q: Vector) -> Vector:
    return [a - b for a, b in zip(p, q, strict=True)]


def scale(a: float, v: Vector) -> Vector:
    return [a * x for x in v]


def norm(v: Vector) -> float:
    return math.sqrt(dot(v, v))


def q_norm(q: Vector) -> Vector:
    n = norm(q)
    if n < 1e-14:
        return [1.0, 0.0, 0.0, 0.0]
    return scale(1.0 / n, q)


def rotate(q: Vector, v: Vector) -> Vector:
    pure = [0.0, v[0], v[1], v[2]]
    return q_mul(q_mul(q_norm(q), pure), q_conj(q_norm(q)))[1:4]


def record_pose(record: dict) -> tuple[Vector, Vector]:
    q_st = q_norm([float(x) for x in record["q_st"]])
    q_dual = [float(x) for x in record["q_dual"]]
    t = scale(2.0, q_mul(q_dual, q_conj(q_st))[1:4])
    return q_st, t


def rotation_error(q1: Vector, q2: Vector) -> float:
    inner = max(0.0, min(1.0, abs(dot(q_norm(q1), q_norm(q2)))))
    argument = max(-1.0, min(1.0, 2.0 * inner * inner - 1.0))
    return float(2.0 * math.acos(argument))


def aligned_errors(truth: list[dict], estimate: list[dict]) -> tuple[float, float]:
    true_q, true_t, est_q, est_t = [], [], [], []
    for tr, est in zip(truth, estimate, strict=True):
        q_t, t_t = record_pose(tr)
        q_e, t_e = record_pose(est)
        true_q.append(q_t)
        true_t.append(t_t)
        est_q.append(q_e)
        est_t.append(t_e)

    # Right-alignment from the paper/Hadi et al.: estimate x truth*z.
    s = [0.0, 0.0, 0.0, 0.0]
    for q_hat, q in zip(true_q, est_q, strict=True):
        s = add(s, q_mul(q_conj(q_hat), q))
    q_align = q_norm(s)
    t_align = [0.0, 0.0, 0.0]
    for q_hat, t_hat, t in zip(true_q, true_t, est_t, strict=True):
        t_align = add(t_align, rotate(q_conj(q_hat), sub(t, t_hat)))
    t_align = scale(1.0 / len(truth), t_align)

    err_r, err_t = [], []
    for q_hat, t_hat, q, t in zip(true_q, true_t, est_q, est_t, strict=True):
        q_right = q_mul(q_hat, q_align)
        t_right = add(t_hat, rotate(q_hat, t_align))
        err_r.append(rotation_error(q, q_right))
        err_t.append(norm(sub(t, t_right)))
    return mean(err_r), mean(err_t)


def mean(values: list[float]) -> float:
    return float(sum(values) / len(values))


def std(values: list[float]) -> float:
    mu = mean(values)
    return math.sqrt(sum((x - mu) ** 2 for x in values) / len(values))


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * q / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[int(position)])
    weight = position - lower
    return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)


def evaluate_artifact(path: Path) -> dict:
    artifact = json.loads(path.read_text())
    err_r, err_t = [], []
    for trial in artifact["trials"]:
        r, t = aligned_errors(trial["truth"], trial["estimate"])
        err_r.append(r)
        err_t.append(t)

    return {
        "experiment": artifact["experiment"],
        "method": artifact["method"],
        "error_R": mean(err_r),
        "error_R_std": std(err_r),
        "error_R_p90": percentile(err_r, 90),
        "error_R_max": max(err_r),
        "error_T": mean(err_t),
        "error_T_std": std(err_t),
        "error_T_p90": percentile(err_t, 90),
        "error_T_max": max(err_t),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", nargs="+", required=True)
    parser.add_argument("--output", default="scoring/scores.json")
    args = parser.parse_args()

    by_exp: dict[str, dict] = {}
    for artifact_path in args.artifacts:
        result = evaluate_artifact(Path(artifact_path))
        exp_name = result.pop("experiment")
        method = result.pop("method")
        by_exp.setdefault(exp_name, {"results": {}})
        by_exp[exp_name]["results"][method] = result

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"experiments": by_exp}, indent=2))
    print(json.dumps({"experiments": by_exp}, indent=2))


if __name__ == "__main__":
    main()
