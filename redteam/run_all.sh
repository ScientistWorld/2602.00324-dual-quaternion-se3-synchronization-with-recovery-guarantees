#!/bin/bash
set -euo pipefail
cd /home/user
# Limit BLAS to one CPU thread for these small matrices. This is a resource
# setting for the candidate computations, not an evaluator environment patch.
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
for case_name in \
  reference_stored_artifacts reference_seed0 reference_seed1 reference_seed2 \
  better_noise_aware weaker_spectral weaker_one_iteration \
  shortcut_rebuild_answers shortcut_rewrite_truth shortcut_bruteforce_seed_bank \
  shortcut_one_pose shortcut_select_trials shortcut_easier_inputs \
  shortcut_replace_baseline shortcut_compensate_failure shortcut_forged_scalars shortcut_constant \
  shortcut_empty shortcut_null shortcut_nan; do
  bash "redteam/${case_name}/run.sh"
done
python3 -m redteam.audit summarize

python3 -m redteam.compare_references
