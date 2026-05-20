#!/usr/bin/env python3
"""Run DQGPM/EIG synthetic experiments and write method artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .sync import run_trial
except ImportError:  # pragma: no cover
    from sync import run_trial


EXPERIMENTS = {
    "p005_noise005": (100, 0.05, 0.05, 5.0),
    "p005_noise010": (100, 0.05, 0.10, 10.0),
    "p008_noise010": (100, 0.08, 0.10, 10.0),
    "p030_noise010": (100, 0.30, 0.10, 10.0),
    "p030_noise005": (100, 0.30, 0.05, 5.0),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", default="p005_noise005", choices=EXPERIMENTS)
    parser.add_argument("--method", default="dqgpm", choices=["dqgpm", "dq_spectral"])
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--max-iter", type=int, default=50)
    parser.add_argument("--output", default="checkpoints/synthetic_results.json")
    parser.add_argument("--seed", type=int, default=260200324)
    parser.add_argument(
        "--record-history",
        action="store_true",
        help="Store every DQGPM iterate for diagnostic plots. Off by default to keep artifacts small.",
    )
    args = parser.parse_args()

    n, p, sigma_t, sigma_r = EXPERIMENTS[args.experiment]
    trials = []
    for trial_idx in range(args.trials):
        seed = args.seed + 7919 * trial_idx
        trials.append(
            run_trial(
                n=n,
                p=p,
                sigma_t=sigma_t,
                sigma_r_deg=sigma_r,
                seed=seed,
                method=args.method,
                max_iter=args.max_iter,
                record_history=args.record_history,
            )
        )

    artifact = {
        "experiment": args.experiment,
        "method": args.method,
        "n": n,
        "p": p,
        "sigma_t": sigma_t,
        "sigma_r_deg": sigma_r,
        "max_iter": args.max_iter,
        "trials": trials,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
