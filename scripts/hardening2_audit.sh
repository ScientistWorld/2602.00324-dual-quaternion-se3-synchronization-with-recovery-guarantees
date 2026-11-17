#!/bin/bash
# Joint hardening audit (CPU): build the real-scan measurements, run the whole
# cohort (reference, comparators, seeds, stronger/weaker controls, shortcut
# probes) through both evaluators, analyze, then regenerate the canonical
# reference-only score files and validate. No training is involved.
set -euo pipefail
cd /home/user
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
if ! python3 -c "import scipy" 2>/dev/null; then
    # Offline fallback when the container predates scipy in setup.sh.
    python3 -m pip install --no-index --no-deps --target tmp/pylib \
        data/downloads/wheels/scipy-1.11.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl || true
    export PYTHONPATH="/home/user/tmp/pylib${PYTHONPATH:+:$PYTHONPATH}"
fi
python3 -c "import numpy, scipy; print('numpy', numpy.__version__, 'scipy', scipy.__version__)" || true
if [[ ! -f eval/test/scans.json || "${REBUILD_SCANS:-0}" == 1 ]]; then python3 eval/test/build_scans.py; fi
if [[ ! -f eval/train/scans.json || "${REBUILD_SCANS:-0}" == 1 ]]; then python3 eval/train/build_scans.py; fi
python3 -m redteam.hardening2.diag_before
python3 -m redteam.hardening2.register
bash scripts/evaluate_train.sh --output redteam/hardening2/scores_train_all.json
bash scripts/evaluate_test.sh --output redteam/hardening2/scores_test_all.json
python3 -m redteam.hardening2.analyze
rm -rf methods/hardening_*
# Canonical artifacts: the reference and the fixed comparators only, rescored
# from the exact raw outputs above (every metric recomputed, nothing rerun).
bash scripts/evaluate_train.sh --reuse-outputs
bash scripts/evaluate_test.sh --reuse-outputs
cp scoring/scores_train.json scoring/scores.json
python3 -m redteam.hardening2.freeze_reference
python3 validate.py --compare --post-design
python3 validate.py --post-reproducer
