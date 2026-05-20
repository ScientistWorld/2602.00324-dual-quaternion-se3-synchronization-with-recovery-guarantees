#!/bin/bash
# Run baseline method (spectral initializer only, EIG-style).
#
# Usage:
#   bash scripts/baseline.sh [experiment] [n_trials]

set -e

cd /home/user

mkdir -p scoring

EXPERIMENT="${1:-sparse_low_noise}"
N_TRIALS="${2:-10}"

# Map experiment names to parameters
case "$EXPERIMENT" in
    sparse_low_noise)
        N=100; P=0.05; SIGMA_T=0.05; SIGMA_R=5; MAX_ITER=50
        ;;
    sparse_mid_noise)
        N=100; P=0.05; SIGMA_T=0.10; SIGMA_R=10; MAX_ITER=50
        ;;
    dense)
        N=100; P=0.30; SIGMA_T=0.10; SIGMA_R=10; MAX_ITER=50
        ;;
    *)
        N=100; P=0.05; SIGMA_T=0.05; SIGMA_R=5; MAX_ITER=50
        ;;
esac

echo "Running EIG baseline on $EXPERIMENT: n=$N, p=$P, sigma_t=$SIGMA_T, sigma_r=$SIGMA_R, trials=$N_TRIALS"

RESULTS=$(python3 -c "
import sys
import json
sys.path.insert(0, 'ev')
from evaluate import evaluate

result = evaluate(
    n=$N,
    p=$P,
    sigma_t=$SIGMA_T,
    sigma_r=$SIGMA_R,
    n_trials=$N_TRIALS,
    method='baseline',
    max_iter_gpm=$MAX_ITER
)
print(json.dumps(result, indent=2))
")

echo "$RESULTS"
