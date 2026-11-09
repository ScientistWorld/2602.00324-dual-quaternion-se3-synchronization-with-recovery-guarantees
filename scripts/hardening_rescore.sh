#!/bin/bash
# One joint check of evaluator-only fixes using final-code raw solver outputs.
set -euo pipefail
cd /home/user
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python3 -m redteam.hardening.protocol_check
python3 -m redteam.hardening.register
bash scripts/evaluate_train.sh --reuse-outputs --output redteam/hardening/scores_train_all.json
bash scripts/evaluate_test.sh --reuse-outputs --output redteam/hardening/scores_test_all.json
python3 -m redteam.hardening.analyze
python3 - <<'PY'
from pathlib import Path
import shutil
for path in Path('methods').glob('hardening_*'):
    shutil.rmtree(path)
PY
# Canonical artifacts contain only the reproduced method and fixed comparisons.
bash scripts/evaluate_train.sh --reuse-outputs
bash scripts/evaluate_test.sh --reuse-outputs
cp scoring/scores_train.json scoring/scores.json
python3 -m redteam.hardening.freeze_reference
python3 -m redteam.hardening.packaging_check
python3 validate.py --compare --post-design
python3 validate.py --post-reproducer
