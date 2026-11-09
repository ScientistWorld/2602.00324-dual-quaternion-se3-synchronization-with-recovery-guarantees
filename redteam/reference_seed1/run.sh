#!/bin/bash
set -euo pipefail
cd /home/user
python3 -m redteam.audit prepare reference_seed1
set +e
bash scripts/evaluate_test.sh >redteam/reference_seed1/test.log 2>&1
test_status=$?
set -e
python3 -m redteam.audit finish reference_seed1 "$test_status"
