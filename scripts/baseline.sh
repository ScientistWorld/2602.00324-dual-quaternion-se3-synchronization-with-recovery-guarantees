#!/bin/bash
# Run the EIG baseline: spectral power initializer followed by projection.

set -euo pipefail
cd /home/user

EXPERIMENT="${1:-p005_noise005}"
TRIALS="${2:-5}"

python3 -m method.run_synthetic \
  --experiment "$EXPERIMENT" \
  --method eig \
  --trials "$TRIALS" \
  --output "checkpoints/${EXPERIMENT}_eig_results.json"
