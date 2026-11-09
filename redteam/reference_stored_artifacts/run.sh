#!/bin/bash
set -euo pipefail
cd /home/user
python3 -m redteam.audit prepare reference_stored_artifacts
set +e
bash scripts/evaluate_test.sh >redteam/reference_stored_artifacts/test.log 2>&1
test_status=$?
set -e
python3 -m redteam.audit finish reference_stored_artifacts "$test_status"
