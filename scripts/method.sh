#!/bin/bash
# Solve an evaluator-provided measurement file.
set -euo pipefail
cd /home/user
python3 -m method.solve "$@"
