#!/usr/bin/env python3
"""Build the pairwise ICP measurements of the public scan-registration train slice.

Paper Section 4.3: relative rigid motions between range scans of the Stanford
3D Scanning Repository are estimated with point-to-point ICP (Besl & McKay),
then perturbed at evaluation time. Ground-truth poses are the repository's own
alignment (the ``.conf`` files). Two graph types are built per object:

* ``sparse``: ICP without any pose prior. Following Besl & McKay's global
  registration strategy, ICP is started from a fixed set of 120 rotations
  (identity plus quasi-uniform samples, centroids aligned); the 3 best coarse
  fits are refined and the best final fit (largest overlap) is kept;
* ``dense``: ICP started from the relative turntable rotation: the angle is
  encoded in the scan file names, about the scan set's turntable axis (bunny
  has no such names, so only ``sparse`` exists).

A pair is observed when ICP converged to the correct registration (overlap of
at least 5% at 1 mm and agreement with the repository alignment within 3 deg
and 5 mm). Among those pairs, the ones with the largest ICP overlap are kept,
up to the number of observed pairs implied by the missing rates in the paper's
Table 4 (missing entries of the n x n measurement matrix); the public slice
keeps the paper's average observed fractions (35% sparse, 82% dense). If that
graph is disconnected, further valid pairs are added by overlap.

The public slice uses scan sets of the repository that the hidden test does
not use (Buddha and dragon placed on their side, back and upright).
Output (committed): ``scans.json`` next to this file. Raw scans are fetched by
``scripts/download.sh`` into ``data/downloads/stanford``.
Run once on a compute node:  python3 eval/train/build_scans.py
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

try:  # fast nearest neighbours when available; exact numpy fallback otherwise
    from scipy.spatial import cKDTree
except Exception:  # pragma: no cover
    cKDTree = None

HERE = Path(__file__).resolve().parent
RAW = HERE.parents[1] / "data" / "downloads" / "stanford"
OUT = HERE / "scans.json"

# (object, directory under RAW, conf file, {mode: observed pairs or fraction})
# Observed pairs follow Table 4: missing = zero entries of the n x n matrix.
SETS = [
    ("buddha_side", "happy_side", "happySideRight.conf", {"dense": 0.82, "sparse": 0.35}),
    ("buddha_back", "happy_back", "happyBackRight.conf", {"dense": 0.82, "sparse": 0.35}),
    ("dragon_side", "dragon_side", "dragonSideRight.conf", {"dense": 0.82, "sparse": 0.35}),
    ("dragon_up", "dragon_up", "dragonUpRight.conf", {"dense": 0.82, "sparse": 0.35}),
]

VOXEL = 0.0025          # source down-sampling (m)
INLIER = 0.001          # overlap / RMSE threshold (m)
D_FINAL = 0.0025        # final max correspondence distance (m)
D_INIT = {"sparse": 0.01, "dense": 0.02}
ITERS = 80
VALID_DEG = 3.0
VALID_M = 0.005
MIN_OVERLAP = 0.05
# Multi-start global search for the no-prior (sparse) graphs.
N_STARTS = 120
COARSE_SRC_VOXEL = 0.008
COARSE_TGT_VOXEL = 0.003
COARSE_ITERS = 25
COARSE_INLIER = 0.004
REFINE_TOP = 3


# ── PLY / conf parsing ───────────────────────────────────────────────────────

_PLY_TYPES = {
    "char": "i1", "int8": "i1", "uchar": "u1", "uint8": "u1",
    "short": "i2", "int16": "i2", "ushort": "u2", "uint16": "u2",
    "int": "i4", "int32": "i4", "uint": "u4", "uint32": "u4",
    "float": "f4", "float32": "f4", "double": "f8", "float64": "f8",
}


def read_ply_vertices(path: Path) -> np.ndarray:
    with open(path, "rb") as fh:
        header = []
        while True:
            line = fh.readline()
            if not line:
                raise ValueError(f"{path}: truncated header")
            text = line.decode("ascii", "replace").strip()
            header.append(text)
            if text == "end_header":
                break
        fmt, elements = None, []
        for text in header:
            tok = text.split()
            if not tok:
                continue
            if tok[0] == "format":
                fmt = tok[1]
            elif tok[0] == "element":
                elements.append([tok[1], int(tok[2]), []])
            elif tok[0] == "property" and elements:
                elements[-1][2].append(tok[1:])
        name, count, props = elements[0]
        if name != "vertex" or any(p[0] == "list" for p in props):
            raise ValueError(f"{path}: unexpected vertex layout")
        names = [p[-1] for p in props]
        cols = [names.index(axis) for axis in ("x", "y", "z")]
        if fmt == "ascii":
            rows = [fh.readline() for _ in range(count)]
            data = np.array(b" ".join(rows).split(), dtype=np.float64).reshape(count, len(props))
            pts = data[:, cols]
        else:
            endian = ">" if fmt == "binary_big_endian" else "<"
            dtype = np.dtype([(f"p{k}", endian + _PLY_TYPES[p[0]]) for k, p in enumerate(props)])
            arr = np.frombuffer(fh.read(dtype.itemsize * count), dtype=dtype, count=count)
            pts = np.stack([arr[f"p{c}"].astype(np.float64) for c in cols], axis=1)
    return pts[np.all(np.isfinite(pts), axis=1)]


def quat_to_rot(q):
    w, x, y, z = np.asarray(q, dtype=np.float64) / np.linalg.norm(q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def rot_to_quat(r):
    r = np.asarray(r, dtype=np.float64)
    tr = np.trace(r)
    cand = [1 + tr, 1 + r[0, 0] - r[1, 1] - r[2, 2], 1 - r[0, 0] + r[1, 1] - r[2, 2], 1 - r[0, 0] - r[1, 1] + r[2, 2]]
    k = int(np.argmax(cand))
    s = 0.5 * math.sqrt(max(cand[k], 1e-300))
    d = 4.0 * s
    if k == 0:
        q = [s, (r[2, 1] - r[1, 2]) / d, (r[0, 2] - r[2, 0]) / d, (r[1, 0] - r[0, 1]) / d]
    elif k == 1:
        q = [(r[2, 1] - r[1, 2]) / d, s, (r[0, 1] + r[1, 0]) / d, (r[0, 2] + r[2, 0]) / d]
    elif k == 2:
        q = [(r[0, 2] - r[2, 0]) / d, (r[0, 1] + r[1, 0]) / d, s, (r[1, 2] + r[2, 1]) / d]
    else:
        q = [(r[1, 0] - r[0, 1]) / d, (r[0, 2] + r[2, 0]) / d, (r[1, 2] + r[2, 1]) / d, s]
    q = np.array(q)
    q /= np.linalg.norm(q)
    return q if q[0] >= 0 else -q


def quat_mul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def quat_conj(a):
    return np.array([a[0], -a[1], -a[2], -a[3]])


def read_conf(path: Path):
    """``bmesh <file> tx ty tz qx qy qz qw`` lines, in file order.

    Returns R(q) for q = (qw, qx, qy, qz); how R and t act on scan points is
    decided from the data (``CONVENTIONS``): for the repository files the
    scan-to-world map is p -> R(q)^T p + t (conjugate quaternion).
    """
    scans = []
    for line in path.read_text().splitlines():
        tok = line.split()
        if len(tok) == 9 and tok[0] == "bmesh":
            t = np.array([float(v) for v in tok[2:5]])
            qx, qy, qz, qw = (float(v) for v in tok[5:9])
            scans.append((tok[1], quat_to_rot([qw, qx, qy, qz]), t))
    return scans


def turntable_angle(name: str):
    match = re.search(r"_(\d+)\.ply$", name)
    return None if match is None else float(match.group(1))


def rodrigues(omega: np.ndarray) -> np.ndarray:
    theta = float(np.linalg.norm(omega))
    if theta < 1e-15:
        return np.eye(3)
    k = omega / theta
    kx = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + math.sin(theta) * kx + (1.0 - math.cos(theta)) * kx @ kx


def rotvec(r: np.ndarray) -> np.ndarray:
    theta = math.acos(max(-1.0, min(1.0, (np.trace(r) - 1.0) / 2.0)))
    if theta < 1e-12:
        return np.zeros(3)
    axis = np.array([r[2, 1] - r[1, 2], r[0, 2] - r[2, 0], r[1, 0] - r[0, 1]]) / (2.0 * math.sin(theta))
    return theta * axis


def wrap_deg(a: float) -> float:
    return (a + 180.0) % 360.0 - 180.0


def turntable_axis(conf, names, convention) -> np.ndarray:
    """Turntable axis in scan coordinates (scanner calibration).

    The angle between two scans is in their file names; the axis is a single
    fixed direction per scan set, read off the repository alignment of scans
    10-170 degrees apart (for the stand sets it is the scanner's -y axis).
    """
    acc = np.zeros(3)
    for i in range(len(conf)):
        for j in range(i + 1, len(conf)):
            delta = wrap_deg(turntable_angle(names[j]) - turntable_angle(names[i]))
            if 10.0 < abs(delta) < 170.0:
                r, _ = gt_pair(conf, i, j, convention)
                acc += rotvec(r) / math.radians(delta)
    return acc / np.linalg.norm(acc)


def angle_deg(r: np.ndarray) -> float:
    return math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(r) - 1.0) / 2.0))))


# ── nearest neighbours and ICP ───────────────────────────────────────────────


class Neighbours:
    def __init__(self, points: np.ndarray):
        self.points = points
        self.tree = cKDTree(points) if cKDTree is not None else None

    def query(self, x: np.ndarray, upper: float):
        if self.tree is not None:
            dist, idx = self.tree.query(x, k=1, distance_upper_bound=upper)
            ok = np.isfinite(dist)
            return dist, np.where(ok, idx, 0), ok
        dist = np.empty(len(x))
        idx = np.empty(len(x), dtype=np.int64)
        p2 = np.einsum("ij,ij->i", self.points, self.points)
        for start in range(0, len(x), 512):
            block = x[start:start + 512]
            d2 = p2[None, :] - 2.0 * block @ self.points.T + np.einsum("ij,ij->i", block, block)[:, None]
            k = np.argmin(d2, axis=1)
            idx[start:start + 512] = k
            dist[start:start + 512] = np.sqrt(np.maximum(d2[np.arange(len(block)), k], 0.0))
        ok = dist <= upper
        return dist, idx, ok


def voxel_downsample(points: np.ndarray, voxel: float) -> np.ndarray:
    keys = np.floor(points / voxel).astype(np.int64)
    _, inverse, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    inverse = inverse.reshape(-1)
    sums = np.zeros((len(counts), 3))
    np.add.at(sums, inverse, points)
    return sums / counts[:, None]


def kabsch(p: np.ndarray, q: np.ndarray):
    pc, qc = p.mean(axis=0), q.mean(axis=0)
    h = (p - pc).T @ (q - qc)
    u, _, vt = np.linalg.svd(h)
    d = np.diag([1.0, 1.0, np.sign(np.linalg.det(vt.T @ u.T)) or 1.0])
    r = vt.T @ d @ u.T
    return r, qc - r @ pc


def icp(src: np.ndarray, target: Neighbours, r: np.ndarray, t: np.ndarray, d_init: float):
    """Point-to-point ICP with a shrinking correspondence gate."""
    it = 0
    for it in range(ITERS):
        gate = max(D_FINAL, d_init * 0.85 ** it)
        moved = src @ r.T + t
        _, idx, ok = target.query(moved, gate)
        if ok.sum() < 30:
            return None
        dr, dt = kabsch(moved[ok], target.points[idx[ok]])
        r, t = dr @ r, dr @ t + dt
        if gate <= D_FINAL and angle_deg(dr) < 1e-7 and np.linalg.norm(dt) < 1e-9:
            break
    moved = src @ r.T + t
    dist, _, ok = target.query(moved, INLIER)
    overlap = float(ok.mean())
    rmse = float(np.sqrt(np.mean(dist[ok] ** 2))) if ok.any() else float("inf")
    return r, t, overlap, rmse, it + 1


def start_rotations() -> list:
    rng = np.random.default_rng(0)
    out = [np.eye(3)]
    while len(out) < N_STARTS:
        q = rng.normal(size=4)
        out.append(quat_to_rot(q / np.linalg.norm(q)))
    return out


def coarse_icp(src: np.ndarray, target: Neighbours, r: np.ndarray, t: np.ndarray):
    for it in range(COARSE_ITERS):
        gate = max(0.006, 0.05 * 0.85 ** it)
        moved = src @ r.T + t
        _, idx, ok = target.query(moved, gate)
        if ok.sum() < 10:
            return None
        dr, dt = kabsch(moved[ok], target.points[idx[ok]])
        r, t = dr @ r, dr @ t + dt
    _, _, ok = target.query(src @ r.T + t, COARSE_INLIER)
    return float(ok.mean()), r, t


def connected(n: int, edges) -> bool:
    adj = [[] for _ in range(n)]
    for i, j in edges:
        adj[i].append(j)
        adj[j].append(i)
    seen, stack = {0}, [0]
    while stack:
        for j in adj[stack.pop()]:
            if j not in seen:
                seen.add(j)
                stack.append(j)
    return len(seen) == n


# ── build ────────────────────────────────────────────────────────────────────


def _stats(values):
    return (float(np.mean(values)), float(np.max(values))) if len(values) else (float("nan"), float("nan"))


def tj_rot(ri, rj, ti, tj):
    # T(p) = R(p + t)  ->  T_i^{-1} T_j (p) = R_i^T R_j (p + t_j) - t_i
    return ri.T @ rj @ tj - ti


def overlap_at(src, target: Neighbours, r, t):
    dist, _, ok = target.query(src @ r.T + t, INLIER)
    return float(ok.mean())


def build_object(obj, folder, conf_name, modes, log):
    conf = read_conf(RAW / folder / conf_name)
    names = [c[0] for c in conf]
    n = len(conf)
    t0 = time.time()
    full = [read_ply_vertices(RAW / folder / name) for name in names]
    small = [voxel_downsample(p, VOXEL) for p in full]
    trees = [Neighbours(p) for p in full]
    coarse_src = [voxel_downsample(p, COARSE_SRC_VOXEL) for p in full]
    coarse_tgt = [Neighbours(voxel_downsample(p, COARSE_TGT_VOXEL)) for p in full]
    centroid = [p.mean(axis=0) for p in full]
    rotations = start_rotations()
    extent = float(np.median([np.linalg.norm(p.max(0) - p.min(0)) for p in full]))
    log(f"{obj}: n={n} points={[len(p) for p in full]} downsampled={[len(p) for p in small]} extent={extent:.3f} m ({time.time()-t0:.1f}s)")

    # Interpret the .conf transform by how well it superimposes neighbours.
    scores = {}
    for convention in CONVENTIONS:
        vals = []
        for i in range(n):
            for j in range(i + 1, n):
                r, t = (gt_pair(conf, i, j, convention))
                vals.append(overlap_at(small[j], trees[i], r, t))
        scores[convention] = float(np.mean(sorted(vals)[-max(3, len(vals) // 3):]))
    convention = max(scores, key=scores.get)
    log(f"{obj}: conf convention overlap {scores} -> {convention}")

    out = []
    for mode, target_count in modes.items():
        results = {}
        t1 = time.time()
        axis = turntable_axis(conf, names, convention) if mode == "dense" else None
        if axis is not None:
            log(f"{obj}: turntable axis in scan coordinates {np.round(axis, 4).tolist()}")
        for i in range(n):
            for j in range(i + 1, n):
                starts = []
                if mode == "dense":
                    delta = wrap_deg(turntable_angle(names[j]) - turntable_angle(names[i]))
                    starts.append((rodrigues(axis * math.radians(delta)), np.zeros(3)))
                else:
                    coarse = [coarse_icp(coarse_src[j], coarse_tgt[i], np.eye(3), np.zeros(3))]
                    coarse += [coarse_icp(coarse_src[j], coarse_tgt[i], r0, centroid[i] - r0 @ centroid[j])
                               for r0 in rotations]
                    coarse = sorted((c for c in coarse if c is not None), key=lambda c: -c[0])[:REFINE_TOP]
                    starts = [(c[1], c[2]) for c in coarse]
                best = None
                for r0, t0_ in starts:
                    res = icp(small[j], trees[i], r0, t0_, D_INIT[mode])
                    if res is not None and (best is None or (res[2], -res[3]) > (best[2], -best[3])):
                        best = res
                if best is None:
                    continue
                r, t, overlap, rmse, iters = best
                rg, tg = gt_pair(conf, i, j, convention)
                err_deg = angle_deg(r.T @ rg)
                err_m = float(np.linalg.norm(t - tg))
                results[(i, j)] = dict(r=r, t=t, overlap=overlap, rmse=rmse, iters=iters,
                                       err_deg=err_deg, err_m=err_m,
                                       valid=bool(overlap >= MIN_OVERLAP and err_deg < VALID_DEG and err_m < VALID_M))
        valid = sorted((k for k, v in results.items() if v["valid"]), key=lambda k: -results[k]["overlap"])
        correct = [v for v in results.values() if v["err_deg"] < VALID_DEG and v["err_m"] < VALID_M]
        wrong = [v for v in results.values() if not (v["err_deg"] < VALID_DEG and v["err_m"] < VALID_M)]
        log(f"{obj}/{mode}: ICP converged to the repository alignment on {len(correct)}/{len(results)} pairs; "
            f"overlap quartiles correct={np.round(np.quantile([v['overlap'] for v in correct], [.25, .5, .75]), 3).tolist() if correct else []} "
            f"wrong={np.round(np.quantile([v['overlap'] for v in wrong], [.25, .5, .75]), 3).tolist() if wrong else []}")
        pairs = n * (n - 1) // 2
        count = int(target_count) if isinstance(target_count, int) else int(round(target_count * pairs))
        kept = valid[:count]
        extra = valid[count:]
        while not connected(n, kept) and extra:
            kept.append(extra.pop(0))
        nodes = list(range(n))
        if not connected(n, kept):
            # keep the largest connected component (documented fallback)
            comps, seen = [], set()
            adj = {i: set() for i in range(n)}
            for i, j in kept:
                adj[i].add(j)
                adj[j].add(i)
            for s in range(n):
                if s in seen:
                    continue
                comp, stack = [], [s]
                seen.add(s)
                while stack:
                    u = stack.pop()
                    comp.append(u)
                    for v in adj[u]:
                        if v not in seen:
                            seen.add(v)
                            stack.append(v)
                comps.append(sorted(comp))
            nodes = max(comps, key=len)
            kept = [(i, j) for i, j in kept if i in nodes and j in nodes]
        index = {old: new for new, old in enumerate(nodes)}
        kept = sorted(kept)
        nn = len(nodes)
        truth = []
        for a in nodes:
            ra, ta = scan_to_world(conf, a, convention)
            # X_a = T_a^{-1}: world -> local frame of scan a.
            if convention.endswith("rotate_then_translate"):
                rx, tx = ra.T, -ra.T @ ta
            else:
                rx, tx = ra.T, -ta
            truth.append([*rot_to_quat(rx).tolist(), *tx.tolist()])
        edges, relative, diag = [], [], []
        for i, j in kept:
            v = results[(i, j)]
            edges.append([index[i], index[j]])
            q = rot_to_quat(v["r"])
            # Unit (dual) quaternions double-cover SE(3). As in the paper's
            # model C_ij = x_i x_j^* + noise, give every measurement the sign
            # consistent with one fixed choice of node representatives (for a
            # connected low-noise graph this lift follows from cycle consistency).
            lift = quat_mul(np.array(truth[index[i]][:4]), quat_conj(np.array(truth[index[j]][:4])))
            if float(np.dot(q, lift)) < 0.0:
                q = -q
            relative.append([*q.tolist(), *v["t"].tolist()])
            diag.append({"overlap": round(v["overlap"], 4), "rmse_m": v["rmse"], "icp_error_deg": v["err_deg"],
                         "icp_error_m": v["err_m"], "iterations": v["iters"]})
        missing = 1.0 - (nn + 2 * len(edges)) / (nn * nn)
        attempted = len(results)
        deg = _stats([d["icp_error_deg"] for d in diag])
        mm = _stats([1e3 * d["icp_error_m"] for d in diag])
        log(f"{obj}/{mode}: attempted={attempted} valid={len(valid)} target={count} kept={len(edges)} n={nn} "
            f"missing={missing:.4f} connected={nn > 1 and connected(nn, edges)} "
            f"icp_err_deg(mean/max)={deg[0]:.3f}/{deg[1]:.3f} icp_err_mm(mean/max)={mm[0]:.3f}/{mm[1]:.3f} "
            f"invalid_converged={sum(1 for v in results.values() if not v['valid'])} ({time.time()-t1:.1f}s)")
        if nn < 5:
            raise SystemExit(f"{obj}/{mode}: only {nn} connected scans survive; check the ICP settings")
        out.append({
            "name": f"{obj}_{mode}", "object": obj, "mode": mode, "n": nn,
            "scans": [names[a] for a in nodes], "conf_convention": convention,
            "truth": truth, "edges": edges, "relative": relative,
            "paper_observed_pairs": target_count if isinstance(target_count, int) else None,
            "valid_pairs": len(valid), "observed_pairs": len(edges), "missing_rate": missing,
            "edge_diagnostics": diag,
        })
    return out


CONVENTIONS = ("conjugate/rotate_then_translate", "conjugate/translate_then_rotate",
               "plain/rotate_then_translate", "plain/translate_then_rotate")


def scan_to_world(conf, a, convention):
    _, r, t = conf[a]
    return (r.T if convention.startswith("conjugate") else r), t


def gt_pair(conf, i, j, convention):
    ri, ti = scan_to_world(conf, i, convention)
    rj, tj = scan_to_world(conf, j, convention)
    if convention.endswith("rotate_then_translate"):
        return ri.T @ rj, ri.T @ (tj - ti)
    return ri.T @ rj, tj_rot(ri, rj, ti, tj)


def main():
    lines = []

    def log(msg):
        print(msg, flush=True)
        lines.append(msg)

    if cKDTree is None and not os.environ.get("ALLOW_SLOW_NEIGHBOURS"):
        raise SystemExit("scipy (cKDTree) is required; set ALLOW_SLOW_NEIGHBOURS=1 to use the slow exact fallback")
    log(f"nearest neighbours: {'scipy cKDTree' if cKDTree is not None else 'numpy brute force'}")
    configs = []
    for obj, folder, conf_name, modes in SETS:
        configs.extend(build_object(obj, folder, conf_name, modes, log))
    payload = {
        "format": "stanford-icp-measurements/v1",
        "source": "https://graphics.stanford.edu/data/3Dscanrep/",
        "pose_convention": "truth X_i maps world to scan i; relative M_ij = X_i X_j^-1 maps scan j into scan i; quaternions scalar-first [w,x,y,z] followed by translation [m]; relative quaternion signs are lifted consistently with the truth representatives",
        "icp": {"voxel_m": VOXEL, "inlier_m": INLIER, "final_gate_m": D_FINAL, "initial_gate_m": D_INIT,
                "iterations": ITERS, "valid_deg": VALID_DEG, "valid_m": VALID_M, "min_overlap": MIN_OVERLAP},
        "configs": configs,
        "log": lines,
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
