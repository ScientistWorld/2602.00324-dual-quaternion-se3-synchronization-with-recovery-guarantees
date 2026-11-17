#!/usr/bin/env python3
"""Public training evaluator for SE(3) synchronization solvers.

Run with no arguments (``bash scripts/evaluate_train.sh``).  At development
time this script builds public instances (synthetic seeds in data/synthetic.py,
scan seeds here), gives every registered solver the same measurement-only
inputs, and scores the returned poses.  Nothing a solver writes is trusted
except its pose estimates.  The hidden test uses the same distributions with
independent seeds and different scan sets.

Experiments:
* four synthetic settings (n=100, Erdos-Renyi measurement graphs conditioned
  on being connected, additive dual-quaternion noise);
* two real-scan settings built from pairwise ICP registrations of public
  Stanford 3D Scanning Repository scan sets (``scans.json`` next to this
  file; Buddha and dragon on side/back/upright): every
  trial re-expresses each scan in an unknown random rigid frame, relabels the
  scans at random, and perturbs every relative pose by a random rigid motion.

Solvers are discovered from ``method/solver.json`` and ``methods/*/solver.json``
(JSON ``{"name": ..., "command": [...]}``; invoked as
``<command> --input IN --output OUT`` from the workspace root).  The
comparators ``dq_spectral``, ``matrix_eig`` and ``sdr`` are computed by this
evaluator itself (``comparators.py``); manifests may not use those names.

Validity rules (any violation fails the whole method): the solver exits 0
within the time limit; the output is strict JSON (no NaN/Infinity, no duplicate
keys) with an estimate for every instance; every estimate has exactly n poses
of four finite numbers each; every pose is a unit dual quaternion
(| |q_st| - 1 | <= 1e-6, |<q_st, q_dual>| <= 1e-6, |q_dual| <= 1e6).  A method
whose mean rotation or translation error on any experiment reaches half the
no-information level (identity rotations, zero translations) has failed the
task. Failed methods receive evaluator-owned worst values for every metric
in every experiment, and a finite rank below all successful attempts.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import shutil
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

SLICE = "train"
# Synthetic settings (n, p, sigma_t, sigma_r_deg) and public test size.
SETTINGS = {
    "p005_noise005": (100, 0.05, 0.05, 5.0),
    "p005_noise010": (100, 0.05, 0.10, 10.0),
    "p008_noise010": (100, 0.08, 0.10, 10.0),
    "p030_noise010": (100, 0.30, 0.10, 10.0),
}
SYNTHETIC_TRIALS = {name: 100 for name in SETTINGS}
# Real-scan settings: ICP graph type, perturbation (paper Table 4: 1 deg, 1 mm).
SCAN_EXPERIMENTS = {"scan_sparse": "sparse", "scan_dense": "dense"}
SCAN_TRIALS_PER_CONFIG = 60
SCAN_SIGMA_T = 0.001
SCAN_SIGMA_R_DEG = 1.0
FRAME_SIGMA_M = 0.05
SCAN_FILE = HERE / "scans.json"
EXPERIMENTS = list(SETTINGS) + list(SCAN_EXPERIMENTS)
_STREAM = {"p005_noise005": 1, "p005_noise010": 2, "p008_noise010": 3, "p030_noise010": 4,
           "scan_sparse": 5, "scan_dense": 6}
_ENTROPY = 260200324  # public development seeds
COMPARATOR_SEED = 0
SOLVER_TIMEOUT_S = 3600
UNIT_TOL = 1e-6
MAX_DUAL_NORM = 1e6
TASK_FAILURE_FRACTION = 0.5
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$")
METRICS = (
    "error_R", "error_R_std", "error_R_p90", "error_R_max",
    "error_T", "error_T_std", "error_T_p90", "error_T_max",
)
INPUT_FORMAT = "se3-sync-measurements/v1"


class InvalidOutput(Exception):
    pass


# ── public instance generators ──────────────────────────────────────────────


def _np_qmul(a, b):
    import numpy as np
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ])


def _np_conj(a):
    import numpy as np
    return np.array([a[0], -a[1], -a[2], -a[3]])


def _np_rot(q):
    import numpy as np
    w, x, y, z = np.asarray(q, dtype=float) / np.linalg.norm(q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def _connected(n, edges):
    adjacency = [[] for _ in range(n)]
    for i, j in edges:
        adjacency[i].append(j)
        adjacency[j].append(i)
    seen, stack = {0}, [0]
    while stack:
        for j in adjacency[stack.pop()]:
            if j not in seen:
                seen.add(j)
                stack.append(j)
    return len(seen) == n


def scan_configs(experiment):
    data = json.loads(SCAN_FILE.read_text())
    return [c for c in data["configs"] if c["mode"] == SCAN_EXPERIMENTS[experiment]]


def _generate_scan(experiment, index, config, k):
    """One perturbation trial of an ICP measurement graph in hidden frames."""
    import numpy as np

    rng = np.random.default_rng(np.random.SeedSequence(_ENTROPY, spawn_key=(_STREAM[experiment], index, k)))
    n = int(config["n"])
    perm = rng.permutation(n)
    frame_q = rng.normal(size=(n, 4))
    frame_q /= np.linalg.norm(frame_q, axis=1, keepdims=True)
    frame_t = rng.normal(scale=FRAME_SIGMA_M, size=(n, 3))
    frame_r = [_np_rot(q) for q in frame_q]
    truth = [None] * n
    for a, row in enumerate(config["truth"]):
        # X_a maps world to scan a; the hidden frame h_a gives h_a X_a.
        q, t = np.array(row[:4]), np.array(row[4:])
        new_q = _np_qmul(frame_q[a], q)
        truth[perm[a]] = ((new_q / np.linalg.norm(new_q)).tolist(), (frame_r[a] @ t + frame_t[a]).tolist())
    observed = []
    for (a, b), row in zip(config["edges"], config["relative"]):
        qm, tm = np.array(row[:4]), np.array(row[4:])
        # Same ICP registration expressed in the hidden frames: h_a M h_b^-1.
        q = _np_qmul(_np_qmul(frame_q[a], qm), _np_conj(frame_q[b]))
        t = frame_r[a] @ (tm - _np_rot(qm) @ frame_r[b].T @ frame_t[b]) + frame_t[a]
        i, j = int(perm[a]), int(perm[b])
        if i > j:
            i, j = j, i
            q, t = _np_conj(q), -_np_rot(q).T @ t
        # Sign-consistent lift of the double cover, as in C_ij = x_i x_j^* + noise.
        if float(np.dot(q, _np_qmul(np.array(truth[i][0]), _np_conj(np.array(truth[j][0]))))) < 0.0:
            q = -q
        axis = rng.normal(size=3)
        axis /= np.linalg.norm(axis)
        angle = np.deg2rad(rng.normal(loc=0.0, scale=SCAN_SIGMA_R_DEG))
        noise_t = rng.normal(loc=0.0, scale=SCAN_SIGMA_T, size=3)
        noise_q = np.array([np.cos(angle / 2.0), *(np.sin(angle / 2.0) * axis)])
        # Rigid perturbation of the relative motion: C = M xi.
        c_q = _np_qmul(q, noise_q)
        c_q /= np.linalg.norm(c_q)
        c_t = _np_rot(q) @ noise_t + t
        observed.append((i, j, c_q.tolist(), (0.5 * _np_qmul(np.array([0.0, *c_t]), c_q)).tolist()))
    observed.sort(key=lambda e: (e[0], e[1]))
    record = {"n": n, "edges": [[i, j] for i, j, _, _ in observed],
              "q_st": [s for _, _, s, _ in observed], "q_dual": [d for _, _, _, d in observed]}
    return record, truth


def setting(experiment):
    if experiment in SETTINGS:
        n, p, sigma_t, sigma_r_deg = SETTINGS[experiment]
        return {"source": "synthetic", "n": n, "p": p, "graph": "connected_erdos_renyi",
                "measurement_model": "additive", "sigma_t": sigma_t, "sigma_r_deg": sigma_r_deg}
    return {"source": "stanford_scans", "graph": SCAN_EXPERIMENTS[experiment],
            "measurement_model": "rigid_perturbation", "sigma_t": SCAN_SIGMA_T, "sigma_r_deg": SCAN_SIGMA_R_DEG}


def build_experiment(experiment):
    """Payload for solvers, scored truth, and the config of every trial."""
    records, scored, groups = [], [], []
    if experiment in SETTINGS:
        if str(WORKSPACE) not in sys.path:
            sys.path.insert(0, str(WORKSPACE))
        from data.synthetic import train_instances, solver_record
        for key, inst in train_instances(experiment, SYNTHETIC_TRIALS[experiment]):
            records.append(solver_record(inst, key))
            scored.append((key, inst.n, [pose(v["q_st"], v["q_dual"]) for v in inst.truth]))
            groups.append(experiment)
    else:
        for index, config in enumerate(scan_configs(experiment)):
            for k in range(SCAN_TRIALS_PER_CONFIG):
                record, truth = _generate_scan(experiment, index, config, k)
                record = {"id": f"{len(records):04d}", **record}
                records.append(record)
                scored.append((record["id"], record["n"], truth))
                groups.append(config["name"])
    payload = {"format": INPUT_FORMAT, "experiment": experiment, "setting": setting(experiment), "instances": records}
    return payload, scored, groups


# ── quaternion arithmetic and metrics (pure Python, scalar-first) ───────────


def q_mul(p, q):
    w1, x1, y1, z1 = p
    w2, x2, y2, z2 = q
    return [
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ]


def q_conj(q):
    return [q[0], -q[1], -q[2], -q[3]]


def dot(p, q):
    return sum(a * b for a, b in zip(p, q))


def norm(v):
    return math.sqrt(dot(v, v))


def rotate(q, v):
    return q_mul(q_mul(q, [0.0, v[0], v[1], v[2]]), q_conj(q))[1:4]


def pose(q_st, q_dual):
    """(unit rotation quaternion, translation) of x = (1 + eps t/2) q."""
    s = norm(q_st)
    q = [c / s for c in q_st]
    t = [2.0 * c / s for c in q_mul(q_dual, q_conj(q))[1:4]]
    return q, t


def rotation_error(q1, q2):
    inner = max(0.0, min(1.0, abs(dot(q1, q2))))
    return 2.0 * math.acos(max(-1.0, min(1.0, 2.0 * inner * inner - 1.0)))


def aligned_errors(truth, estimate):
    """Mean rotation/translation error after the paper's right gauge alignment.

    The aligning rotation is q = s/|s| with s = sum_j q^_j* q_j (Hadi et al.),
    with each term's sign chosen consistently (q and -q are the same rotation,
    so the score must not depend on the double-cover sign of any pose).
    """
    # Fix the estimate's right-translation gauge before applying the paper's
    # alignment. Otherwise the score changes under t_i -> t_i + R_i u even
    # though every relative pose is unchanged. The reference already uses this
    # convention; applying it here makes the metric independent of the solver.
    body = [rotate(q_conj(q), t) for q, t in estimate]
    origin = [sum(v[k] for v in body) / len(body) for k in range(3)]
    estimate = [(q, [t[k] - shift[k] for k in range(3)])
                for q, t in estimate for shift in [rotate(q, origin)]]
    terms = [q_mul(q_conj(qh), q) for (qh, _), (q, _) in zip(truth, estimate)]
    s = [sum(t[k] for t in terms) for k in range(4)]
    if norm(s) < 1e-9:
        s = list(terms[0])
    signs = None
    for _ in range(50):
        new_signs = [1.0 if dot(t, s) >= 0.0 else -1.0 for t in terms]
        if new_signs == signs:
            break
        signs = new_signs
        s = [sum(g * t[k] for g, t in zip(signs, terms)) for k in range(4)]
    if norm(s) < 1e-12:
        s = [1.0, 0.0, 0.0, 0.0]
    q_align = [c / norm(s) for c in s]
    n = len(truth)
    t_align = [0.0, 0.0, 0.0]
    for (qh, th), (_, t) in zip(truth, estimate):
        d = rotate(q_conj(qh), [t[0] - th[0], t[1] - th[1], t[2] - th[2]])
        t_align = [a + b for a, b in zip(t_align, d)]
    t_align = [c / n for c in t_align]
    err_r = err_t = 0.0
    for (qh, th), (q, t) in zip(truth, estimate):
        err_r += rotation_error(q, q_mul(qh, q_align))
        shift = rotate(qh, t_align)
        err_t += norm([t[k] - th[k] - shift[k] for k in range(3)])
    return err_r / n, err_t / n


def _percentile(values, q):
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    pos = (len(ordered) - 1) * q / 100.0
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return float(ordered[lo])
    w = pos - lo
    return float(ordered[lo] * (1.0 - w) + ordered[hi] * w)


def summarize(err_r, err_t):
    out = {}
    for prefix, vals in (("error_R", err_r), ("error_T", err_t)):
        mu = sum(vals) / len(vals)
        out[prefix] = mu
        out[f"{prefix}_std"] = math.sqrt(sum((v - mu) ** 2 for v in vals) / len(vals))
        out[f"{prefix}_p90"] = _percentile(vals, 90)
        out[f"{prefix}_max"] = max(vals)
    return {k: out[k] for k in METRICS}



# ── strict parsing of solver output ─────────────────────────────────────────


def strict_json(text):
    def pairs_hook(pairs):
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)):
            raise InvalidOutput("duplicate JSON key")
        return dict(pairs)

    def bad_constant(name):
        raise InvalidOutput(f"non-finite JSON constant {name}")

    return json.loads(text, object_pairs_hook=pairs_hook, parse_constant=bad_constant)


def _quaternions(value, n, label):
    if not isinstance(value, list) or len(value) != n:
        raise InvalidOutput(f"{label} must list exactly {n} quaternions")
    rows = []
    for row in value:
        if not isinstance(row, list) or len(row) != 4:
            raise InvalidOutput(f"{label} entries must have 4 components")
        vals = []
        for x in row:
            if isinstance(x, bool) or not isinstance(x, (int, float)):
                raise InvalidOutput(f"{label} has a non-numeric component")
            try:
                x = float(x)
            except OverflowError as exc:
                raise InvalidOutput(f"{label} component overflows") from exc
            if not math.isfinite(x):
                raise InvalidOutput(f"{label} has a non-finite component")
            vals.append(x)
        rows.append(vals)
    return rows


def parse_poses(entry, n):
    if not isinstance(entry, dict) or set(entry) != {"q_st", "q_dual"}:
        raise InvalidOutput("estimate must be an object with q_st and q_dual")
    q_st = _quaternions(entry.get("q_st"), n, "q_st")
    q_dual = _quaternions(entry.get("q_dual"), n, "q_dual")
    poses = []
    for a, b in zip(q_st, q_dual):
        if abs(norm(a) - 1.0) > UNIT_TOL:
            raise InvalidOutput("pose is not a unit dual quaternion (|q_st| != 1)")
        if abs(dot(a, b)) > UNIT_TOL:
            raise InvalidOutput("pose is not a unit dual quaternion (<q_st, q_dual> != 0)")
        if norm(b) > MAX_DUAL_NORM:
            raise InvalidOutput("translation magnitude out of range")
        poses.append(pose(a, b))
    return poses


def score_output(data, instances):
    if not isinstance(data, dict) or set(data) != {"estimates"} or not isinstance(data.get("estimates"), dict):
        raise InvalidOutput("output must be an object with an 'estimates' object")
    estimates = data["estimates"]
    if set(estimates) != {inst_id for inst_id, _, _ in instances}:
        raise InvalidOutput("instance IDs must match the complete fixed test exactly")
    err_r, err_t = [], []
    for inst_id, n, truth in instances:
        if inst_id not in estimates:
            raise InvalidOutput(f"missing estimate for instance {inst_id}")
        r, t = aligned_errors(truth, parse_poses(estimates[inst_id], n))
        err_r.append(r)
        err_t.append(t)
    return err_r, err_t



# All baselines, settings, rank definitions, and reference poses are owned here.
CACHE = Path(__file__).resolve().parent / ".cache"


def _load_comparators():
    path = Path(__file__).resolve().parent / "comparators.py"
    spec = importlib.util.spec_from_file_location(f"se3_{SLICE}_comparators", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def discover_manifests():
    paths = [WORKSPACE / "method" / "solver.json"]
    # A missing primary manifest is a failed attempt, not an empty submission
    # that earns the reference score by omitting all candidate metrics.
    return paths + sorted((WORKSPACE / "methods").glob("*/solver.json"))


def load_manifest(path, reserved):
    data = strict_json(Path(path).read_text())
    name, command = data.get("name"), data.get("command")
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        raise InvalidOutput("invalid solver name")
    if name in reserved or name.startswith("invalid_manifest_"):
        raise InvalidOutput("name is reserved for a fixed evaluator comparator")
    if not isinstance(command, list) or not command or not all(isinstance(c, str) and c for c in command):
        raise InvalidOutput("command must be a non-empty list of strings")
    return {"name": name, "command": command, "source": str(path)}


def run_solver(manifest, payload, directory):
    directory.mkdir(parents=True, exist_ok=True)
    inp, out, log = directory / "input.json", directory / "output.json", directory / "solver.log"
    try:
        inp.write_text(json.dumps(payload))
        with log.open("w") as fh:
            try:
                proc = subprocess.run([*manifest["command"], "--input", str(inp), "--output", str(out)],
                                      cwd=WORKSPACE, stdout=fh, stderr=subprocess.STDOUT, timeout=SOLVER_TIMEOUT_S)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise InvalidOutput(f"solver execution failed: {exc}") from exc
        if proc.returncode != 0:
            raise InvalidOutput(f"solver exit {proc.returncode}; {log.read_text(errors='replace')[-300:]}")
        if not out.is_file():
            raise InvalidOutput("missing raw output")
        return out.read_text()
    finally:
        # Only one experiment's files need exist, and hidden inputs stay here.
        shutil.rmtree(directory, ignore_errors=True)


def raw_comparator(fn, payload):
    estimates = {}
    for k, record in enumerate(payload["instances"]):
        st, du = fn(record, COMPARATOR_SEED+k, payload["setting"])
        estimates[record["id"]] = {"q_st": st.tolist(), "q_dual": du.tolist()}
    return json.dumps({"estimates": estimates}, allow_nan=False)


def cached_raw(name, exp, payload, producer, reuse):
    folder = CACHE / name / exp
    folder.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    rawfile, keyfile = folder / "raw.json", folder / "input.sha256"
    if reuse:
        if not rawfile.is_file() or not keyfile.is_file() or keyfile.read_text() != digest:
            raise InvalidOutput("no raw output cached for these exact inputs")
        return rawfile.read_text()
    raw = producer()
    rawfile.write_text(raw)
    keyfile.write_text(digest)
    return raw


def task_failure(metrics, noinfo, experiments):
    for exp in experiments:
        v = metrics.get(exp, {})
        if set(v) != set(METRICS) or any(not math.isfinite(x) or x < 0 for x in v.values()):
            return f"{exp}: invalid or incomplete measured metrics"
        if v["error_R_max"] > 2*math.pi + 1e-8:
            return f"{exp}: impossible rotation error"
        if any(v[key] >= TASK_FAILURE_FRACTION*noinfo[exp][key] for key in ("error_R", "error_T")):
            return f"{exp}: failed rotation or translation task threshold"
    return None


def failure_values(noinfo, counts):
    """Finite values no passing attempt can beat in the worse direction.

    If N nonnegative trial errors have mean below L, max < N*L,
    std < sqrt(N-1)*L, and the interpolated p90 < N*L/(N-ceil(.9*(N-1))).
    Rotation errors also lie in [0, 2*pi], so std <= pi. The small margin
    makes penalties strictly worse even at a physical boundary. These are
    failure sentinels, never presented as measured pose errors.
    """
    penalties = {}
    for exp, n in counts.items():
        penalties[exp] = {}
        for prefix in ("error_R", "error_T"):
            limit = TASK_FAILURE_FRACTION * noinfo[exp][prefix]
            bounds = {
                "": limit,
                "_std": math.sqrt(n-1)*limit,
                "_p90": n*limit / max(1, n-math.ceil(.9*(n-1))),
                "_max": n*limit,
            }
            if prefix == "error_R":
                bounds = {suffix: min(v, math.pi if suffix == "_std" else 2*math.pi)
                          for suffix, v in bounds.items()}
            for suffix, bound in bounds.items():
                penalties[exp][prefix+suffix] = 1.01*bound + 1e-9
    return penalties


def finalized_metrics(measured, failure, penalties):
    # A failure anywhere invalidates the whole run. Do not leave successful
    # prefixes, empty experiments, or low dispersion values in scored results.
    return {e: dict(v) for e, v in (penalties if failure else measured).items()}


def normalized_ranks(metrics, statuses, anchor, config):
    """Rank every candidate, including fully populated failure penalties.

    Coefficient magnitude sets importance; direction comes from the metric.
    All candidate attempts on disk and the fixed anchor enter the population
    scale. Comparators are evaluator-owned diagnostics, not candidate attempts.
    Componentwise worse failure sentinels guarantee failure cannot compensate
    through another metric, including for consumers that ignore status flags.
    """
    names = [n for n in metrics if not statuses[n].get("evaluator_owned")]
    ranks = {n: 0.0 for n in names}
    scales = {}
    for exp, spec in config["experiments"].items():
        scales[exp] = {}
        for key, definition in spec["metrics"].items():
            a = anchor[exp][key]
            values = [a] + [metrics[n][exp][key] for n in names]
            mu = sum(values)/len(values)
            sd = math.sqrt(sum((v-mu)**2 for v in values)/len(values))
            scales[exp][key] = sd
            if sd == 0:
                continue
            direction = 1.0 if definition["higher_is_better"] else -1.0
            coefficient = abs(definition["coefficient"])*spec["weight"]
            for name in names:
                ranks[name] += coefficient*direction*(metrics[name][exp][key]-a)/sd
    return ranks, scales


def per_group_means(err_r, err_t, groups):
    out = {}
    for g in dict.fromkeys(groups):
        idx = [k for k, x in enumerate(groups) if x == g]
        out[g] = {"error_R": sum(err_r[k] for k in idx)/len(idx), "error_T": sum(err_t[k] for k in idx)/len(idx),
                  "trials": len(idx)}
    return out


def main():
    parser = argparse.ArgumentParser(description="Score every solver on fixed measurement-only instances.")
    parser.add_argument("--output", default=f"scoring/scores_{SLICE}.json")
    parser.add_argument("--reuse-outputs", action="store_true", help="recompute every metric from saved raw outputs")
    args = parser.parse_args()
    module = _load_comparators()
    config = strict_json((Path(__file__).resolve().parent / "ranking.json").read_text())
    if list(config["experiments"]) != EXPERIMENTS:
        raise RuntimeError("ranking.json experiments do not match the evaluator")
    manifests, rejected, counts = [], [], {}
    for path in discover_manifests():
        try:
            manifest = load_manifest(path, set(module.COMPARATORS) | {"_reference"})
            manifests.append(manifest)
            counts[manifest["name"]] = counts.get(manifest["name"], 0)+1
        except Exception as exc:
            rejected.append({"source":str(path), "reason":str(exc), "status":"failed", "rank":None})
    duplicates = {name for name, count in counts.items() if count != 1}
    for manifest in manifests:
        if manifest["name"] in duplicates:
            rejected.append({"source":manifest["source"], "reason":"duplicate solver name", "status":"failed", "rank":None})
    manifests = [m for m in manifests if m["name"] not in duplicates]
    payloads, scored, groups, noinfo, trials = {}, {}, {}, {}, {}
    for exp in EXPERIMENTS:
        payloads[exp], scored[exp], groups[exp] = build_experiment(exp)
        trials[exp] = len(scored[exp])
        errs = [aligned_errors(truth, [([1.,0.,0.,0.], [0.,0.,0.])]*n) for _, n, truth in scored[exp]]
        noinfo[exp] = summarize([v[0] for v in errs], [v[1] for v in errs])
    penalties = failure_values(noinfo, trials)
    metrics, statuses, details, diagnostics, group_means = {}, {}, {}, {}, {}
    # Rejected manifests must still cost a complete failed attempt. Their IDs
    # are evaluator-owned so invalid/reserved/duplicate names cannot overwrite
    # a fixed comparator or a valid method's results.
    for rejected_entry in rejected:
        name = "invalid_manifest_" + hashlib.sha256(rejected_entry["source"].encode()).hexdigest()[:12]
        rejected_entry["result_name"] = name
        metrics[name] = finalized_metrics({}, True, penalties)
        statuses[name] = {**rejected_entry, "evaluator_owned": False,
                          "constraints": {"complete_valid_outputs": False}}
    jobs = [("_reference", module.reference, None)]
    jobs += [(name, fn, None) for name, fn in module.COMPARATORS.items()]
    jobs += [(m["name"], None, m) for m in manifests]
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp_root = Path(tempfile.mkdtemp(prefix="solver_", dir=CACHE))
    try:
        for name, fn, manifest in jobs:
            # Comparators run only where the paper runs them (SDR: real scans).
            required = [e for e in EXPERIMENTS if fn is None or module.applies(name, e)]
            measured, pertrial, failure = {}, {}, None
            print(f"[{SLICE}] evaluating {name}", flush=True)
            for exp in required:
                try:
                    def produce():
                        return raw_comparator(fn, payloads[exp]) if fn else run_solver(manifest, payloads[exp], tmp_root/name/exp)
                    raw = cached_raw(name, exp, payloads[exp], produce, args.reuse_outputs)
                    r, t = score_output(strict_json(raw), scored[exp])
                    measured[exp] = summarize(r,t)
                    pertrial[exp] = {"error_R":r, "error_T":t}
                    if exp in SCAN_EXPERIMENTS:
                        group_means.setdefault(name, {})[exp] = per_group_means(r, t, groups[exp])
                except OSError as exc:
                    raise RuntimeError(f"evaluator I/O failed for {name}/{exp}: {exc}") from exc
                except Exception as exc:
                    failure = f"{exp}: {type(exc).__name__}: {exc}"
                    break
            failure = failure or task_failure(measured, noinfo, required)
            if failure:
                metrics[name] = finalized_metrics(measured, failure, {e: penalties[e] for e in required})
            else:
                metrics[name] = finalized_metrics(measured, failure, penalties)
            details[name], diagnostics[name] = pertrial, measured
            statuses[name] = {"status":"failed" if failure else "ok", "evaluator_owned":fn is not None,
                              "source":f"eval/{SLICE}/comparators.py" if fn else manifest["source"]}
            statuses[name]["constraints"] = {
                "complete_valid_outputs": len(measured) == len(required),
                "recovery_fraction_threshold": TASK_FAILURE_FRACTION,
                "recovery_fractions": {exp: {
                    "rotation":v["error_R"]/max(noinfo[exp]["error_R"], 1e-300),
                    "translation":v["error_T"]/max(noinfo[exp]["error_T"], 1e-300)}
                    for exp,v in measured.items()},
            }
            if failure:
                statuses[name]["reason"] = failure
                print(f"[{SLICE}] {name} FAILED: {failure}", flush=True)
            # Save progress after each solver.
            (CACHE/"details.json").write_text(json.dumps(details, allow_nan=False))
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
    anchor = metrics.pop("_reference")
    anchor_status = statuses.pop("_reference")
    group_means.pop("_reference", None)
    if anchor_status["status"] != "ok":
        raise RuntimeError(f"frozen reference failed: {anchor_status}")
    ranks, scales = normalized_ranks(metrics, statuses, anchor, config)
    for name in statuses:
        statuses[name]["rank"] = ranks.get(name)
    result = {"_metadata": {"slice":SLICE, "evaluator":f"eval/{SLICE}/evaluate.py", "trials":trials,
        "methods":statuses, "rejected_manifests":rejected, "no_information":noinfo,
        "reference":anchor, "failure_values":penalties, "measured_before_failure":{
            n:diagnostics.get(n,{}) for n,v in statuses.items() if v["status"] != "ok"},
        "scan_config_means":group_means,
        "rank_scales":scales, "rank_definition":"sum weight*abs(coefficient)*direction*(value-reference)/cohort_population_std; every candidate including failed attempts; failures have worst values in all metrics"},
        "experiments": {exp:{"slice":SLICE,"n_trials":trials[exp],
                             "results":{n:m[exp] for n,m in metrics.items() if exp in m}} for exp in EXPERIMENTS}}
    out = Path(args.output)
    if not out.is_absolute():
        out = WORKSPACE/out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(f"[{SLICE}] saved {out}", flush=True)


if __name__ == "__main__":
    main()
