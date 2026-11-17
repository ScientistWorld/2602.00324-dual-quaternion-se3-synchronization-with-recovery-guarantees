#!/bin/bash
set -euo pipefail
# Setup may source this file at the host workspace path before the runtime
# /home/user bind exists. Resolve the downloaded dependencies from this file.
# numpy is the only runtime dependency of solvers and evaluators; scipy is
# used only by eval/*/build_scans.py (nearest neighbours for ICP).
se3_setup_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
se3_wheel_dir="$se3_setup_root/data/downloads/wheels"
if [[ -f "$se3_wheel_dir/numpy-1.26.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl" \
   && -f "$se3_wheel_dir/scipy-1.11.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl" ]]; then
    uv pip install --system --no-index --find-links "$se3_wheel_dir" numpy==1.26.4 scipy==1.11.4
else
    # Environment setup has internet; compute jobs do not. A fresh clone may
    # install before download.sh has populated its offline wheels.
    uv pip install --system numpy==1.26.4 scipy==1.11.4
fi
