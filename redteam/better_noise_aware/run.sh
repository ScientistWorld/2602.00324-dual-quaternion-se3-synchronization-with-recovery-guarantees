#!/bin/bash
set -euo pipefail
cd /home/user
python3 -m redteam.audit prepare better_noise_aware
set +e
bash scripts/evaluate_test.sh >redteam/better_noise_aware/test.log 2>&1
test_status=$?
set -e
python3 -m redteam.audit finish better_noise_aware "$test_status"
