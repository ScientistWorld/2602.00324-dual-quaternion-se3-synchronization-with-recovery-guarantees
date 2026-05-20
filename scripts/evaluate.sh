#!/bin/bash
# Score method artifacts without importing method code.

set -euo pipefail
cd /home/user

if [ "$#" -eq 0 ]; then
  set -- checkpoints/*_results.json
fi

python3 eval/evaluate.py --artifacts "$@" --output scoring/scores.json
