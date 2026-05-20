#!/usr/bin/env python3
"""Held-out test-slice scorer for SE(3) synchronization artifacts.

This evaluator reads method result artifacts only. It does not import or run
method code. The held-out slice uses the complement of the visible seed
partition: ``trial_seed % 7 >= 3``.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


SLICE = "test"
TRIAL_SELECTOR = "seed_mod_7_gte_3"


def _load_main_evaluator():
    path = Path(__file__).resolve().parents[1] / "evaluate.py"
    spec = importlib.util.spec_from_file_location("se3_main_evaluator", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load evaluator from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MAIN_EVAL = _load_main_evaluator()


def select_trials(trials: list[dict]) -> list[dict]:
    selected = [
        trial
        for trial in trials
        if int(trial.get("seed", 0)) % 7 >= 3
    ]
    if not selected:
        raise ValueError("test slice has no trials to score")
    return selected


def evaluate_artifact(path: Path) -> dict:
    artifact = json.loads(path.read_text())
    err_r, err_t = [], []
    for trial in select_trials(artifact["trials"]):
        r, t = MAIN_EVAL.aligned_errors(trial["truth"], trial["estimate"])
        err_r.append(r)
        err_t.append(t)

    return {
        "experiment": artifact["experiment"],
        "method": artifact["method"],
        "error_R": MAIN_EVAL.mean(err_r),
        "error_R_std": MAIN_EVAL.std(err_r),
        "error_R_p90": MAIN_EVAL.percentile(err_r, 90),
        "error_R_max": max(err_r),
        "error_T": MAIN_EVAL.mean(err_t),
        "error_T_std": MAIN_EVAL.std(err_t),
        "error_T_p90": MAIN_EVAL.percentile(err_t, 90),
        "error_T_max": max(err_t),
    }


def reference_entries(path: Path) -> tuple[set[str], set[tuple[str, str]]]:
    if not path.exists():
        return set(), set()
    data = json.loads(path.read_text())
    experiments = data.get("experiments", {})
    entries = {
        (exp_name, method_name)
        for exp_name, exp_data in experiments.items()
        for method_name in exp_data.get("results", {})
    }
    return set(experiments), entries


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

    allowed_experiments, allowed_entries = reference_entries(Path(args.reference))
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
        if allowed_entries and entry not in allowed_entries:
            continue
        if expected and entry not in expected:
            continue
        seen.add(entry)
        by_exp.setdefault(
            exp_name,
            {
                "slice": SLICE,
                "trial_selector": TRIAL_SELECTOR,
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
