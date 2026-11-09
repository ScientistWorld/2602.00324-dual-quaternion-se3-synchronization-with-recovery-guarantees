#!/bin/bash
set -euo pipefail
cd /home/user
python3 -m redteam.audit prepare shortcut_one_pose
set +e
bash scripts/evaluate_test.sh >redteam/shortcut_one_pose/test.log 2>&1
test_status=$?
set -e
python3 -m redteam.audit finish shortcut_one_pose "$test_status"
