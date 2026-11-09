#!/bin/bash
set -euo pipefail
cd /home/user
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python3 eval/train/evaluate.py --output scoring/scores_train.json "$@"
