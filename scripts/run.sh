#!/bin/bash
# Compute-node entrypoint. Runs the core synthetic reproduction and scores it.

set -euo pipefail
cd /home/user

mkdir -p checkpoints scoring

TRIALS="${TRIALS:-100}"
EXPERIMENTS=(p005_noise005 p005_noise010 p030_noise010)
ARTIFACTS=()

for exp in "${EXPERIMENTS[@]}"; do
  bash scripts/method.sh "$exp" "$TRIALS"
  bash scripts/baseline.sh "$exp" "$TRIALS"
  ARTIFACTS+=("checkpoints/${exp}_dqgpm_results.json")
  ARTIFACTS+=("checkpoints/${exp}_dq_spectral_results.json")
done

bash scripts/evaluate.sh "${ARTIFACTS[@]}"
python3 validate.py --compare
