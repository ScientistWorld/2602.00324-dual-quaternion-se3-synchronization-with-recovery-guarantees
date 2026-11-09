"""Shared helpers for the public baseline solvers (no dependency on method/)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

import numpy as np

CONJ = np.array([1.0, -1.0, -1.0, -1.0])
IDENTITY = np.array([1.0, 0.0, 0.0, 0.0])


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


def run_cli(solve: Callable[[dict, int], tuple[np.ndarray, np.ndarray]], description: str) -> None:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text())
    estimates = {}
    for index, instance in enumerate(payload["instances"]):
        q_st, q_dual = solve(instance, args.seed + index)
        estimates[instance["id"]] = {"q_st": np.asarray(q_st).tolist(), "q_dual": np.asarray(q_dual).tolist()}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"estimates": estimates}))
