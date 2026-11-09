#!/bin/bash
set -euo pipefail
cd /home/user
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python3 eval/test/evaluate.py --output scoring/scores_test.json "$@"
