#!/usr/bin/env python3
"""Visible train-slice scorer for SE(3) synchronization artifacts.

This evaluator reads method result artifacts only. It does not import or run
method code. The visible slice uses a deterministic seed partition:
``trial_seed % 7 < 3``. The complementary held-out slice is implemented in
``eval/test/evaluate.py``.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


SLICE = "train"
TRIAL_SELECTOR = "seed_mod_7_lt_3"


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
        if int(trial.get("seed", 0)) % 7 < 3
    ]
    if not selected:
        raise ValueError("train slice has no trials to score")
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", nargs="+", required=True)
    parser.add_argument("--output", default="scoring/scores_train.json")
    parser.add_argument("--reference", default="scoring/reference.json")
    args = parser.parse_args()

    allowed_experiments, allowed_entries = reference_entries(Path(args.reference))
    by_exp: dict[str, dict] = {}
    for artifact_path in args.artifacts:
        result = evaluate_artifact(Path(artifact_path))
        exp_name = result.pop("experiment")
        if allowed_experiments and exp_name not in allowed_experiments:
            continue
        method = result.pop("method")
        if allowed_entries and (exp_name, method) not in allowed_entries:
            continue
        by_exp.setdefault(
            exp_name,
            {
                "slice": SLICE,
                "trial_selector": TRIAL_SELECTOR,
                "results": {},
            },
        )
        by_exp[exp_name]["results"][method] = result

    payload = {"_metadata": {"slice": SLICE}, "experiments": by_exp}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
