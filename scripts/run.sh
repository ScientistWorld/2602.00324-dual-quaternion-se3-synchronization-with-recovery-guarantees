#!/bin/bash
# Compute-node entrypoint for regenerating the core artifacts, refreshing
# scores, and probing the next synthetic settings for possible expansion.

set -euo pipefail
cd /home/user

mkdir -p checkpoints outputs scoring

# Regenerate the scored core suite from scratch.  Checkpoints are gitignored,
# so run.sh must not depend on artifacts left by a previous job.
bash scripts/reproduce.sh 100 200

python3 validate.py --compare --post-reproducer

# Probe additional Table 2 settings without overwriting the validated core
# scores.  These artifacts are evaluated into tmp/ for analysis after the job.
for exp in p008_noise010 p030_noise005 p030_noise010; do
  bash scripts/method.sh "$exp" 100 200
  bash scripts/baseline.sh "$exp" 100
done

python3 eval/evaluate.py \
  --artifacts \
  checkpoints/p008_noise010_dqgpm_results.json \
  checkpoints/p008_noise010_dq_spectral_results.json \
  checkpoints/p030_noise005_dqgpm_results.json \
  checkpoints/p030_noise005_dq_spectral_results.json \
  checkpoints/p030_noise010_dqgpm_results.json \
  checkpoints/p030_noise010_dq_spectral_results.json \
  --output tmp/extension_scores.json
