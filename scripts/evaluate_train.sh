#!/bin/bash
# Score visible train-slice method artifacts without importing method code.

set -euo pipefail
cd /home/user

if [ "$#" -eq 0 ]; then
  shopt -s nullglob
  artifacts=(checkpoints/*_results.json outputs/*_results.json)
  shopt -u nullglob
  if [ "${#artifacts[@]}" -eq 0 ]; then
    echo "No result artifacts found in checkpoints/ or outputs/. Run scripts/method.sh or pass artifact paths." >&2
    exit 2
  fi
  set -- "${artifacts[@]}"
fi

python3 eval/train/evaluate.py --artifacts "$@" --output scoring/scores_train.json
