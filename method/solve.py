#!/usr/bin/env python3
"""Solver entry point registered in method/solver.json.

Reads a measurement-only input file (see briefing/evaluation.md) and writes one
unit-dual-quaternion pose per node for every instance:

    python3 -m method.solve --input in.json --output out.json

The pipeline is the paper's: Algorithm 1 (power iteration, residual < 1e-5)
followed by Algorithm 2 (DQGPM with per-iteration projection onto UDQ^n).
The initializer's random start uses seed ``--seed + instance_index`` so runs
are deterministic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from method.sync import solve_instance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--stage", choices=["dqgpm", "spectral"], default="dqgpm")
    parser.add_argument("--init-tol", type=float, default=1e-5)
    parser.add_argument("--init-max-iter", type=int, default=2000)
    parser.add_argument("--gpm-tol", type=float, default=1e-8)
    parser.add_argument("--gpm-max-iter", type=int, default=200)
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text())
    estimates = {}
    for index, instance in enumerate(payload["instances"]):
        q_st, q_dual = solve_instance(
            instance,
            seed=args.seed + index,
            stage=args.stage,
            init_tol=args.init_tol,
            init_max_iter=args.init_max_iter,
            gpm_tol=args.gpm_tol,
            gpm_max_iter=args.gpm_max_iter,
        )
        estimates[instance["id"]] = {"q_st": q_st.tolist(), "q_dual": q_dual.tolist()}

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"estimates": estimates}))


if __name__ == "__main__":
    main()
