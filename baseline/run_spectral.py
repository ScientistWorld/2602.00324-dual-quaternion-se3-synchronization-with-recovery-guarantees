#!/usr/bin/env python3
"""Run the rounded dual-quaternion spectral initializer baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from method.run_synthetic import EXPERIMENTS
from method.sync import run_trial


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", default="p005_noise005", choices=EXPERIMENTS)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--output", default="checkpoints/spectral_baseline_results.json")
    parser.add_argument("--seed", type=int, default=260200324)
    args = parser.parse_args()

    n, p, sigma_t, sigma_r = EXPERIMENTS[args.experiment]
    trials = []
    for trial_idx in range(args.trials):
        trials.append(
            run_trial(
                n=n,
                p=p,
                sigma_t=sigma_t,
                sigma_r_deg=sigma_r,
                seed=args.seed + 7919 * trial_idx,
                method="dq_spectral",
            )
        )

    artifact = {
        "experiment": args.experiment,
        "method": "dq_spectral",
        "n": n,
        "p": p,
        "sigma_t": sigma_t,
        "sigma_r_deg": sigma_r,
        "trials": trials,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
