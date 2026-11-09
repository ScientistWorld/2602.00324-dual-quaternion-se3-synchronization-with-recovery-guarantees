#!/usr/bin/env python3
"""Public training evaluator for SE(3) synchronization solvers.

Run with no arguments (``bash scripts/evaluate_test.sh``).  At test time this
script draws fresh instances from the benchmark distribution with public seeds in data/synthetic.py, gives every registered solver the same measurement-only
inputs, and scores the returned poses against truth that never leaves this
process.  Nothing a solver writes is trusted except its pose estimates.

Solvers are discovered from ``method/solver.json`` and ``methods/*/solver.json``
(JSON ``{"name": ..., "command": [...]}``; invoked as
``<command> --input IN --output OUT`` from the workspace root).  The
comparators ``dq_spectral`` and ``matrix_eig`` are computed by this evaluator
itself (``comparators.py``); manifests may not use those names.

Validity rules (any violation fails the whole method): the solver exits 0
within the time limit; the output is strict JSON (no NaN/Infinity, no duplicate
keys) with an estimate for every instance; every estimate has exactly n poses
of four finite numbers each; every pose is a unit dual quaternion
(| |q_st| - 1 | <= 1e-6, |<q_st, q_dual>| <= 1e-6, |q_dual| <= 1e6).  A method
whose mean rotation or translation error on any experiment reaches half the
no-information level (identity rotations, zero translations) has failed the
task.  Failed methods have no rank; valid raw measurements remain available for diagnosis.
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

SLICE = "train"
# Experiment settings (n, p, sigma_t, sigma_r_deg) and hidden test size.
SETTINGS = {
    "p005_noise005": (100, 0.05, 0.05, 5.0),
    "p005_noise010": (100, 0.05, 0.10, 10.0),
    "p008_noise010": (100, 0.08, 0.10, 10.0),
    "p030_noise010": (100, 0.30, 0.10, 10.0),
}
TRIALS = {name: 100 for name in SETTINGS}
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


# ── hidden instance generator (same distribution as the public one) ─────────


def build_experiment(experiment):
    if str(WORKSPACE) not in sys.path:
        sys.path.insert(0, str(WORKSPACE))
    from data.synthetic import train_instances, solver_input
    labelled = train_instances(experiment, TRIALS[experiment])
    payload = solver_input(experiment, labelled)
    scored = [(key, inst.n, [pose(v["q_st"],v["q_dual"]) for v in inst.truth]) for key,inst in labelled]
    return payload, scored


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
    return [p for p in paths if p.is_file()] + sorted((WORKSPACE / "methods").glob("*/solver.json"))


def load_manifest(path, reserved):
    data = strict_json(Path(path).read_text())
    name, command = data.get("name"), data.get("command")
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        raise InvalidOutput("invalid solver name")
    if name in reserved:
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
        st, du = fn(record, COMPARATOR_SEED+k)
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


def task_failure(metrics, noinfo):
    for exp in SETTINGS:
        v = metrics.get(exp, {})
        if set(v) != set(METRICS) or any(not math.isfinite(x) or x < 0 for x in v.values()):
            return f"{exp}: invalid or incomplete measured metrics"
        if v["error_R_max"] > 2*math.pi + 1e-8:
            return f"{exp}: impossible rotation error"
        if any(v[key] >= TASK_FAILURE_FRACTION*noinfo[exp][key] for key in ("error_R", "error_T")):
            return f"{exp}: failed rotation or translation task threshold"
    return None


def normalized_ranks(metrics, statuses, anchor, config):
    """Only successful attempts enter the population scale; reference is fixed.

    Each coefficient's magnitude determines importance. Unit changes therefore
    do not change rank. Failed tasks have rank None and sort below all passes.
    """
    names = [n for n in metrics if statuses[n]["status"] == "ok" and not statuses[n].get("evaluator_owned")]
    ranks = {n: (0.0 if statuses[n]["status"] == "ok" else None) for n in names}
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
    for name in metrics:
        if statuses[name]["status"] != "ok":
            ranks[name] = None
    return ranks, scales


def main():
    parser = argparse.ArgumentParser(description="Score every solver on fixed measurement-only instances.")
    parser.add_argument("--output", default=f"scoring/scores_{SLICE}.json")
    parser.add_argument("--reuse-outputs", action="store_true", help="recompute every metric from saved raw outputs")
    args = parser.parse_args()
    module = _load_comparators()
    config = strict_json((Path(__file__).resolve().parent / "ranking.json").read_text())
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
    payloads, scored, noinfo = {}, {}, {}
    for exp in SETTINGS:
        payloads[exp], scored[exp] = build_experiment(exp)
        identity = [([1.,0.,0.,0.], [0.,0.,0.])]*SETTINGS[exp][0]
        errs = [aligned_errors(truth, identity) for _, _, truth in scored[exp]]
        noinfo[exp] = summarize([v[0] for v in errs], [v[1] for v in errs])
    metrics, statuses, details = {}, {}, {}
    jobs = [("_reference", module.reference, None)]
    jobs += [(name, fn, None) for name, fn in module.COMPARATORS.items()]
    jobs += [(m["name"], None, m) for m in manifests]
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp_root = Path(tempfile.mkdtemp(prefix="solver_", dir=CACHE))
    try:
        for name, fn, manifest in jobs:
            measured, pertrial, failure = {}, {}, None
            print(f"[{SLICE}] evaluating {name}", flush=True)
            for exp in SETTINGS:
                try:
                    def produce():
                        return raw_comparator(fn, payloads[exp]) if fn else run_solver(manifest, payloads[exp], tmp_root/name/exp)
                    raw = cached_raw(name, exp, payloads[exp], produce, args.reuse_outputs)
                    r, t = score_output(strict_json(raw), scored[exp])
                    measured[exp] = summarize(r,t)
                    pertrial[exp] = {"error_R":r, "error_T":t}
                except OSError as exc:
                    raise RuntimeError(f"evaluator I/O failed for {name}/{exp}: {exc}") from exc
                except Exception as exc:
                    failure = f"{exp}: {type(exc).__name__}: {exc}"
                    break
            failure = failure or task_failure(measured, noinfo)
            metrics[name], details[name] = measured, pertrial
            statuses[name] = {"status":"failed" if failure else "ok", "evaluator_owned":fn is not None,
                              "source":f"eval/{SLICE}/comparators.py" if fn else manifest["source"]}
            statuses[name]["constraints"] = {
                "complete_valid_outputs": len(measured) == len(SETTINGS),
                "recovery_fraction_threshold": TASK_FAILURE_FRACTION,
                "recovery_fractions": {exp: {
                    "rotation":v["error_R"]/noinfo[exp]["error_R"],
                    "translation":v["error_T"]/noinfo[exp]["error_T"]}
                    for exp,v in measured.items()},
            }
            if failure:
                statuses[name]["reason"] = failure
                print(f"[{SLICE}] {name} FAILED: {failure}", flush=True)
            # Save progress after each solver. Per-trial errors and all raw
            # answers on the hidden side stay inside eval/train/.
            (CACHE/"details.json").write_text(json.dumps(details, allow_nan=False))
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
    anchor = metrics.pop("_reference")
    anchor_status = statuses.pop("_reference")
    if anchor_status["status"] != "ok":
        raise RuntimeError(f"frozen reference failed: {anchor_status}")
    ranks, scales = normalized_ranks(metrics, statuses, anchor, config)
    for name in statuses:
        statuses[name]["rank"] = ranks.get(name)
    result = {"_metadata": {"slice":SLICE, "evaluator":f"eval/{SLICE}/evaluate.py", "trials":TRIALS,
        "methods":statuses, "rejected_manifests":rejected, "no_information":noinfo,
        "reference":anchor, "rank_scales":scales, "rank_definition":"sum weight*abs(coefficient)*direction*(value-reference)/cohort_population_std; failures unranked"},
        "experiments": {exp:{"slice":SLICE,"n_trials":TRIALS[exp],"results":{n:m.get(exp,{}) for n,m in metrics.items()}} for exp in SETTINGS}}
    out = Path(args.output)
    if not out.is_absolute():
        out = WORKSPACE/out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(f"[{SLICE}] saved {out}", flush=True)


if __name__ == "__main__":
    main()
