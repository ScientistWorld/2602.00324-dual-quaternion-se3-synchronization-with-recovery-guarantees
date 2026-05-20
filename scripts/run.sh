#!/bin/bash
# Compute-node entrypoint for train/test split scoring.

set -euo pipefail
cd /home/user

mkdir -p scoring

bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
