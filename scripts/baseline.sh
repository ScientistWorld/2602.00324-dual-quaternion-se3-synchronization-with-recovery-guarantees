#!/bin/bash
# Run the dual-quaternion rounded spectral initializer baseline.

set -euo pipefail
cd /home/user

EXPERIMENT="${1:-p005_noise005}"
TRIALS="${2:-5}"

python3 -m baseline.run_spectral \
  --experiment "$EXPERIMENT" \
  --trials "$TRIALS" \
  --output "checkpoints/${EXPERIMENT}_dq_spectral_results.json"
