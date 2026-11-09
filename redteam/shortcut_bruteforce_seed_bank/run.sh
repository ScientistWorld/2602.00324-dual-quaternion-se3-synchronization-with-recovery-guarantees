#!/bin/bash
set -euo pipefail
cd /home/user
python3 -m redteam.audit prepare shortcut_bruteforce_seed_bank
set +e
bash scripts/evaluate_test.sh >redteam/shortcut_bruteforce_seed_bank/test.log 2>&1
test_status=$?
set -e
python3 -m redteam.audit finish shortcut_bruteforce_seed_bank "$test_status"
