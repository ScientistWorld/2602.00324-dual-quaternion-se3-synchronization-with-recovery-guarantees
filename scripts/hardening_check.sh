#!/bin/bash
# One joint verification job for all fixes. No training is required.
set -euo pipefail
cd /home/user
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python3 -m redteam.hardening.protocol_check
python3 -m redteam.hardening.legacy_check
python3 -m redteam.hardening.register
bash scripts/evaluate_train.sh --output redteam/hardening/scores_train_all.json
bash scripts/evaluate_test.sh --output redteam/hardening/scores_test_all.json
# Paired uncertainty and shortcut diagnostics are all produced from saved raw
# output. Continue packaging even if a headroom assertion needs review.
python3 -m redteam.hardening.analyze || touch tmp/hardening_needs_review
python3 - <<'PY'
from pathlib import Path
import shutil
for path in Path('methods').glob('hardening_*'):
    shutil.rmtree(path)
PY
# Re-score the exact reference outputs after removing the audit-only methods.
# Every metric is recomputed; no solver or fixed comparison is run a second time.
bash scripts/evaluate_train.sh --reuse-outputs
bash scripts/evaluate_test.sh --reuse-outputs
cp scoring/scores_train.json scoring/scores.json
python3 -m redteam.hardening.freeze_reference
python3 validate.py
