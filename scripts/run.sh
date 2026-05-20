#!/bin/bash
# Compute-node entrypoint.  Runs a small core-claim reproduction and scores it.

set -euo pipefail
cd /home/user

mkdir -p checkpoints scoring

# Smoke-test scale: enough trials to verify the full DQGPM pipeline while
# staying comfortably inside a test-node allocation.
bash scripts/method.sh p005_noise005 5
bash scripts/baseline.sh p005_noise005 5
bash scripts/evaluate.sh checkpoints/p005_noise005_*_results.json
python3 validate.py --compare
