#!/bin/bash
set -euo pipefail
cd /home/user
python3 -m redteam.audit prepare weaker_one_iteration
set +e
bash scripts/evaluate_test.sh >redteam/weaker_one_iteration/test.log 2>&1
test_status=$?
set -e
python3 -m redteam.audit finish weaker_one_iteration "$test_status"
