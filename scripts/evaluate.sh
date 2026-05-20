#!/bin/bash
# Evaluation script — the standard way to evaluate work in this environment.
#
# This script evaluates SE(3) synchronization methods on synthetic data.
# It runs the specified method on multiple trials and computes error metrics.
#
# OUTPUT: writes scoring/scores.json with reproduced results.
#
# Usage:
#   ./evaluate.sh                             # defaults: n=100, p=0.05, st=0.05, sr=5, 10 trials
#   ./evaluate.sh dqgpm sparse_low_noise     # named experiment
#   ./evaluate.sh dqgpm sparse_low_noise 50  # 50 trials

set -e

cd /home/user

mkdir -p scoring

METHOD="${1:-dqgpm}"
EXPERIMENT="${2:-sparse_low_noise}"
N_TRIALS="${3:-10}"

# Map experiment names to parameters
case "$EXPERIMENT" in
    sparse_low_noise)
        N=100; P=0.05; SIGMA_T=0.05; SIGMA_R=5; MAX_ITER=50
        ;;
    sparse_mid_noise)
        N=100; P=0.05; SIGMA_T=0.10; SIGMA_R=10; MAX_ITER=50
        ;;
    medium)
        N=100; P=0.08; SIGMA_T=0.10; SIGMA_R=10; MAX_ITER=50
        ;;
    dense)
        N=100; P=0.30; SIGMA_T=0.10; SIGMA_R=10; MAX_ITER=50
        ;;
    dense_low_noise)
        N=100; P=0.30; SIGMA_T=0.05; SIGMA_R=5; MAX_ITER=50
        ;;
    *)
        N=100; P=0.05; SIGMA_T=0.05; SIGMA_R=5; MAX_ITER=50
        ;;
esac

echo "Evaluating $METHOD on $EXPERIMENT: n=$N, p=$P, sigma_t=$SIGMA_T, sigma_r=$SIGMA_R, trials=$N_TRIALS"

# Run evaluation
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
    method='$METHOD',
    max_iter_gpm=$MAX_ITER
)
print(json.dumps(result, indent=2))
")

echo "$RESULTS"

# Write scores.json
cat > scoring/scores.json << EOF
{
  "experiments": {
    "$EXPERIMENT": {
      "n": $N,
      "p": $P,
      "sigma_t": $SIGMA_T,
      "sigma_r": $SIGMA_R,
      "n_trials": $N_TRIALS,
      "results": {
        "$METHOD": {
          "type": "$( [ '$METHOD' = 'dqgpm' ] && echo 'proposed' || echo 'baseline' )",
          "error_R": $(echo "$RESULTS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d[\"error_R_mean\"]:.6f}')"),
          "error_R_std": $(echo "$RESULTS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d[\"error_R_std\"]:.6f}')"),
          "error_T": $(echo "$RESULTS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d[\"error_T_mean\"]:.6f}')"),
          "error_T_std": $(echo "$RESULTS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d[\"error_T_std\"]:.6f}')")
        }
      }
    }
  }
}
EOF

echo "Results written to scoring/scores.json"
