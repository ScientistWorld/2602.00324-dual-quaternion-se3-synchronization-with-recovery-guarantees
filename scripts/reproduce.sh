#!/bin/bash
# End-to-end, from raw scans and generators to reference and fixed baseline scores.
set -euo pipefail
cd /home/user
bash scripts/download.sh
# The ICP measurement graphs are committed; rebuild them only if missing.
[[ -f eval/test/scans.json ]] || python3 eval/test/build_scans.py
[[ -f eval/train/scans.json ]] || python3 eval/train/build_scans.py
bash scripts/evaluate.sh
bash scripts/evaluate_test.sh
python3 validate.py
