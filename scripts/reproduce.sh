#!/bin/bash
# End-to-end reproduction for the core synthetic claim.

set -euo pipefail
cd /home/user

TRIALS="${1:-100}"
MAX_ITER="${2:-200}"
EXPERIMENTS=(p005_noise005 p005_noise010)

for exp in "${EXPERIMENTS[@]}"; do
  bash scripts/method.sh "$exp" "$TRIALS" "$MAX_ITER"
  bash scripts/baseline.sh "$exp" "$TRIALS"
done

bash scripts/evaluate.sh \
  checkpoints/p005_noise005_dqgpm_results.json \
  checkpoints/p005_noise005_dq_spectral_results.json \
  checkpoints/p005_noise010_dqgpm_results.json \
  checkpoints/p005_noise010_dq_spectral_results.json
