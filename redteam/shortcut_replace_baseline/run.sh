#!/bin/bash
set -euo pipefail
cd /home/user
python3 -m redteam.audit prepare shortcut_replace_baseline
set +e
bash scripts/evaluate_test.sh >redteam/shortcut_replace_baseline/test.log 2>&1
test_status=$?
set -e
python3 -m redteam.audit finish shortcut_replace_baseline "$test_status"
