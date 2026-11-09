#!/bin/bash
set -euo pipefail
cd /home/user
python3 -m redteam.audit prepare shortcut_rebuild_answers
set +e
bash scripts/evaluate_test.sh >redteam/shortcut_rebuild_answers/test.log 2>&1
test_status=$?
set -e
python3 -m redteam.audit finish shortcut_rebuild_answers "$test_status"
