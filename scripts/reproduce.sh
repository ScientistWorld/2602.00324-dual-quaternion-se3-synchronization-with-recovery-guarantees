#!/bin/bash
# End-to-end reproduction for the core synthetic claim.

set -euo pipefail
cd /home/user

TRIALS="${1:-20}"
EXPERIMENTS=(p005_noise005 p005_noise010 p030_noise010)

for exp in "${EXPERIMENTS[@]}"; do
  bash scripts/method.sh "$exp" "$TRIALS"
  bash scripts/baseline.sh "$exp" "$TRIALS"
done

bash scripts/evaluate.sh checkpoints/*_results.json
