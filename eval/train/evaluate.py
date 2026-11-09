#!/usr/bin/env python3
"""Visible train-slice evaluator for SE(3) synchronization solvers.

Instances come from the public generator and the visible seed family in
``data/synthetic.py`` (the original 100-trial protocol).  Every registered
solver is run on measurement-only inputs through the solver interface
(``<command> --input IN --output OUT``) and scored against truth that never
leaves this process.

Solvers are discovered from manifests (JSON ``{"name": ..., "command": [...]}``):
``method/solver.json``, ``methods/*/solver.json`` and, on the train side only,
the public baseline manifests ``baseline/solvers/*.json``.

Validity rules (any violation fails the whole method): the solver exits 0
within the time limit; the output is strict JSON (no NaN/Infinity, no duplicate
keys) with an estimate for every instance; every estimate has exactly n poses
of four finite numbers each; every pose is a unit dual quaternion
(| |q_st| - 1 | <= 1e-6, |<q_st, q_dual>| <= 1e-6, |q_dual| <= 1e6).  A method
whose mean rotation or translation error on any experiment reaches half the
no-information level (identity rotations, zero translations) has failed the
task.  Failed methods get fixed worst-case metrics on every experiment.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

SLICE = "train"
EXPERIMENTS = ("p005_noise005", "p005_noise010", "p008_noise010", "p030_noise010")
TRIALS = 100
SOLVER_TIMEOUT_S = 3600
UNIT_TOL = 1e-6
MAX_DUAL_NORM = 1e6
TASK_FAILURE_FRACTION = 0.5
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$")
METRICS = (
    "error_R", "error_R_std", "error_R_p90", "error_R_max",
    "error_T", "error_T_std", "error_T_p90", "error_T_max",
)


class InvalidOutput(Exception):
    pass


# ── quaternion arithmetic (pure Python, scalar-first) ───────────────────────


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


def failure_metrics(noinfo):
    """Fixed worst-case values: rotation errors at their bound (2*pi, std pi),
    translation errors at twice the no-information mean error."""
    bad_t = 2.0 * noinfo["error_T"]
    return {
        "error_R": 2 * math.pi, "error_R_std": math.pi, "error_R_p90": 2 * math.pi, "error_R_max": 2 * math.pi,
        "error_T": bad_t, "error_T_std": bad_t, "error_T_p90": bad_t, "error_T_max": bad_t,
    }


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
    if not isinstance(entry, dict):
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
    if not isinstance(data, dict) or not isinstance(data.get("estimates"), dict):
        raise InvalidOutput("output must be an object with an 'estimates' object")
    estimates = data["estimates"]
    err_r, err_t = [], []
    for inst_id, n, truth in instances:
        if inst_id not in estimates:
            raise InvalidOutput(f"missing estimate for instance {inst_id}")
        r, t = aligned_errors(truth, parse_poses(estimates[inst_id], n))
        err_r.append(r)
        err_t.append(t)
    return err_r, err_t


# ── solver discovery and execution ──────────────────────────────────────────


def discover_manifests():
    paths = []
    main = WORKSPACE / "method" / "solver.json"
    if main.is_file():
        paths.append(main)
    paths += sorted((WORKSPACE / "methods").glob("*/solver.json"))
    paths += sorted((WORKSPACE / "baseline" / "solvers").glob("*.json"))
    return paths


def load_manifest(path):
    data = strict_json(Path(path).read_text())
    name, command = data.get("name"), data.get("command")
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise InvalidOutput(f"invalid solver name {name!r}")
    if not isinstance(command, list) or not command or not all(isinstance(c, str) and c for c in command):
        raise InvalidOutput("command must be a non-empty list of strings")
    try:
        source = str(Path(path).resolve().relative_to(WORKSPACE))
    except ValueError:
        source = str(path)
    return {"name": name, "command": command, "source": source}


def run_solver(manifest, payload, workdir, timeout):
    workdir.mkdir(parents=True, exist_ok=True)
    inp, out, log = workdir / "input.json", workdir / "output.json", workdir / "solver.log"
    inp.write_text(json.dumps(payload))
    cmd = [*manifest["command"], "--input", str(inp), "--output", str(out)]
    with log.open("w") as fh:
        try:
            proc = subprocess.run(cmd, cwd=WORKSPACE, stdout=fh, stderr=subprocess.STDOUT, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None, f"solver exceeded {timeout} s"
        except OSError as exc:
            return None, f"solver could not start: {exc}"
    if proc.returncode != 0:
        tail = log.read_text(errors="replace")[-600:]
        return None, f"solver exited with code {proc.returncode}: {tail}"
    if not out.is_file():
        return None, "solver wrote no output file"
    try:
        return strict_json(out.read_text()), None
    except Exception as exc:  # noqa: BLE001 - any unparsable output is a failure
        return None, f"unparsable output: {exc}"


# ── instances ───────────────────────────────────────────────────────────────


def build_instances(experiment, trials):
    from data.synthetic import solver_input, train_instances

    labelled = train_instances(experiment, trials)
    payload = solver_input(experiment, labelled)
    scored = []
    for inst_id, inst in labelled:
        truth = [pose(r["q_st"], r["q_dual"]) for r in inst.truth]
        scored.append((inst_id, inst.n, truth))
    return payload, scored


def main():
    parser = argparse.ArgumentParser(description="Score solvers on the visible train family.")
    parser.add_argument("--output", default="scoring/scores_train.json")
    parser.add_argument("--trials", type=int, default=TRIALS)
    parser.add_argument("--experiments", nargs="+", default=list(EXPERIMENTS), choices=list(EXPERIMENTS))
    parser.add_argument("--solver-manifest", action="append", default=None,
                        help="score only these manifests (default: discover all)")
    parser.add_argument("--details", help="optional path for per-trial errors")
    parser.add_argument("--timeout", type=int, default=SOLVER_TIMEOUT_S)
    args = parser.parse_args()

    manifests, rejected, seen = [], [], set()
    for path in args.solver_manifest or discover_manifests():
        try:
            m = load_manifest(path)
        except Exception as exc:  # noqa: BLE001
            rejected.append({"source": str(path), "reason": str(exc)})
            continue
        if m["name"] in seen:
            rejected.append({"source": m["source"], "reason": f"duplicate solver name {m['name']}"})
            continue
        seen.add(m["name"])
        manifests.append(m)
    if not manifests:
        raise SystemExit("No solver manifests found (expected method/solver.json).")

    payloads, scored, noinfo = {}, {}, {}
    for exp in args.experiments:
        payloads[exp], scored[exp] = build_instances(exp, args.trials)
        identity = [([1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0])] * scored[exp][0][1]
        errs = [aligned_errors(truth, identity[: len(truth)]) for _, _, truth in scored[exp]]
        noinfo[exp] = summarize([e[0] for e in errs], [e[1] for e in errs])

    experiments = {
        exp: {"slice": SLICE, "n_trials": len(scored[exp]), "results": {}} for exp in args.experiments
    }
    status, details = {}, {}
    tmp_root = Path(tempfile.mkdtemp(prefix="se3_train_"))
    try:
        for m in manifests:
            per_exp, failure = {}, None
            for exp in args.experiments:
                data, err = run_solver(m, payloads[exp], tmp_root / m["name"] / exp, args.timeout)
                if err is None:
                    try:
                        per_exp[exp] = score_output(data, scored[exp])
                    except InvalidOutput as exc:
                        err = str(exc)
                if err is not None:
                    failure = f"{exp}: {err}"
                    break
            if failure is None:
                for exp in args.experiments:
                    summ = summarize(*per_exp[exp])
                    ref = noinfo[exp]
                    if (summ["error_R"] >= TASK_FAILURE_FRACTION * ref["error_R"]
                            or summ["error_T"] >= TASK_FAILURE_FRACTION * ref["error_T"]):
                        failure = (f"{exp}: task failure (error_R={summ['error_R']:.4f}, "
                                   f"error_T={summ['error_T']:.4f}; no-information level "
                                   f"{ref['error_R']:.4f}/{ref['error_T']:.4f})")
                        break
            for exp in args.experiments:
                experiments[exp]["results"][m["name"]] = (
                    failure_metrics(noinfo[exp]) if failure else summarize(*per_exp[exp])
                )
            status[m["name"]] = {"status": "failed" if failure else "ok", "source": m["source"]}
            if failure:
                status[m["name"]]["reason"] = failure
                print(f"[{SLICE}] {m['name']} FAILED: {failure}", file=sys.stderr)
            else:
                details[m["name"]] = {exp: {"error_R": per_exp[exp][0], "error_T": per_exp[exp][1]}
                                      for exp in args.experiments}
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)

    payload = {
        "_metadata": {
            "slice": SLICE,
            "evaluator": "eval/train/evaluate.py",
            "trials": {exp: len(scored[exp]) for exp in args.experiments},
            "methods": status,
            "rejected_manifests": rejected,
            "no_information": noinfo,
        },
        "experiments": experiments,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    if args.details:
        Path(args.details).parent.mkdir(parents=True, exist_ok=True)
        Path(args.details).write_text(json.dumps(details))
    print(json.dumps(payload["experiments"], indent=2))


if __name__ == "__main__":
    main()
