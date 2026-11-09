#!/bin/bash
# End-to-end, from raw measurements to reference and fixed baseline scores.
set -euo pipefail
cd /home/user
bash scripts/download.sh
bash scripts/evaluate.sh
bash scripts/evaluate_test.sh
python3 validate.py
