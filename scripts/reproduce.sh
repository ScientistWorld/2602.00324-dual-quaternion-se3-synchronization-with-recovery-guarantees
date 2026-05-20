#!/bin/bash
# Reproduce the paper's results end-to-end.
#
# This script runs DQGPM and baseline methods on all experiment settings
# and generates the final scoring/scores.json.

set -e

cd /home/user

echo "=== SE(3) Synchronization Reproduction ==="

# Run DQGPM on all experiment settings
echo "Running DQGPM..."
bash scripts/evaluate.sh dqgpm sparse_low_noise 20
bash scripts/evaluate.sh dqgpm sparse_mid_noise 20
bash scripts/evaluate.sh dqgpm dense 20

# Run baseline (spectral initializer only)
echo "Running baseline (EIG)..."
bash scripts/evaluate.sh baseline sparse_low_noise 20

echo ""
echo "=== Reproduction Complete ==="
echo "Results in scoring/scores.json"
