#!/bin/bash
set -euo pipefail
cd /home/user
bash scripts/evaluate_train.sh "$@"
cp scoring/scores_train.json scoring/scores.json
