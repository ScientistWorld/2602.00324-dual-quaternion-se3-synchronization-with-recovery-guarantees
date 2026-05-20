#!/bin/bash
# Compute-node entrypoint for refreshing artifact scores and validation.

set -euo pipefail
cd /home/user

mkdir -p scoring

bash scripts/evaluate.sh \
  checkpoints/p005_noise005_dqgpm_results.json \
  checkpoints/p005_noise005_dq_spectral_results.json \
  checkpoints/p005_noise010_dqgpm_results.json \
  checkpoints/p005_noise010_dq_spectral_results.json

python3 validate.py --compare --post-reproducer
