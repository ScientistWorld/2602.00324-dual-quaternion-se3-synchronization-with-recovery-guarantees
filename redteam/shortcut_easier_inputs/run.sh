#!/bin/bash
set -euo pipefail
cd /home/user
python3 -m redteam.audit prepare shortcut_easier_inputs
set +e
bash scripts/evaluate_test.sh >redteam/shortcut_easier_inputs/test.log 2>&1
test_status=$?
set -e
python3 -m redteam.audit finish shortcut_easier_inputs "$test_status"
