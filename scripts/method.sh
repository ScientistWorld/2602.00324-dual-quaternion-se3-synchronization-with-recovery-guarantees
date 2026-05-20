#!/bin/bash
# Run the paper's DQGPM method on one synthetic benchmark setting.

set -euo pipefail
cd /home/user

EXPERIMENT="${1:-p005_noise005}"
TRIALS="${2:-5}"
MAX_ITER="${3:-50}"

python3 -m method.run_synthetic \
  --experiment "$EXPERIMENT" \
  --method dqgpm \
  --trials "$TRIALS" \
  --max-iter "$MAX_ITER" \
  --output "checkpoints/${EXPERIMENT}_dqgpm_results.json"
