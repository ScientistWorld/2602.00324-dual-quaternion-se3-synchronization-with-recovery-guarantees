#!/bin/bash
set -euo pipefail
cd /home/user
python3 -m redteam.audit prepare shortcut_select_trials
set +e
bash scripts/evaluate_test.sh >redteam/shortcut_select_trials/test.log 2>&1
test_status=$?
set -e
python3 -m redteam.audit finish shortcut_select_trials "$test_status"
