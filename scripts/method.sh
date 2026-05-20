#!/bin/bash
# Run the paper's proposed method (DQGPM).
#
# Usage:
#   bash scripts/method.sh

set -e

cd /home/user

echo "Running DQGPM on synthetic data..."

# Run on key experiment settings
for experiment in sparse_low_noise sparse_mid_noise dense; do
    echo "=== $experiment ==="
    bash scripts/evaluate.sh dqgpm $experiment 10
done

echo "Method evaluation complete."
