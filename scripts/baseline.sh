#!/bin/bash
# Run the dual-quaternion rounded spectral initializer baseline.

set -euo pipefail
cd /home/user

EXPERIMENT="${1:-p005_noise005}"
TRIALS="${2:-5}"

python3 -m method.run_synthetic \
  --experiment "$EXPERIMENT" \
  --method dq_spectral \
  --trials "$TRIALS" \
  --output "checkpoints/${EXPERIMENT}_dq_spectral_results.json"
