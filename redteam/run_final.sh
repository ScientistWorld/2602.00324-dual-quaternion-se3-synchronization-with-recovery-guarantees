#!/bin/bash
set -euo pipefail
cd /home/user
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
bash redteam/shortcut_forged_scalars/run.sh
python3 -m redteam.protocol_diagnostics
python3 -m redteam.audit summarize
