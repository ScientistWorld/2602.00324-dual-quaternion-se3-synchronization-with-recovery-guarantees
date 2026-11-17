#!/bin/bash
# Evaluator-only fix: recompute every metric of the whole audit cohort from the
# raw outputs saved by scripts/hardening2_audit.sh (exact input fingerprints
# are checked; no solver or comparator is rerun), then regenerate the
# canonical reference-only scores and validate.
set -euo pipefail
cd /home/user
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python3 -m redteam.hardening2.register
bash scripts/evaluate_train.sh --reuse-outputs --output redteam/hardening2/scores_train_all.json
bash scripts/evaluate_test.sh --reuse-outputs --output redteam/hardening2/scores_test_all.json
python3 -m redteam.hardening2.analyze
rm -rf methods/hardening_*
bash scripts/evaluate_train.sh --reuse-outputs
bash scripts/evaluate_test.sh --reuse-outputs
cp scoring/scores_train.json scoring/scores.json
python3 -m redteam.hardening2.freeze_reference
python3 validate.py --compare --post-design
python3 validate.py --post-reproducer
