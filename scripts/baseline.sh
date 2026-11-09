#!/bin/bash
set -euo pipefail
cd /home/user
python3 -m baseline.dq_spectral "$@"
