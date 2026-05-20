#!/bin/bash
# Run evaluation inside compute container.

set -e

cd /home/user

# Run DQGPM on key experiment settings
echo "=== Running DQGPM Evaluation ==="

# Run on sparse settings (paper's main claim)
for p in 0.05 0.08 0.30; do
    for sigma_t in 0.05 0.10; do
        sigma_r=$((sigma_t == 0.05 ? 5 : 10))
        echo "Running p=$p, sigma_t=$sigma_t, sigma_r=$sigma_r"
        python3 -c "
import sys, json
sys.path.insert(0, 'ev')
from evaluate import evaluate

result = evaluate(n=100, p=$p, sigma_t=$sigma_t, sigma_r=$sigma_r, n_trials=20, method='dqgpm', max_iter_gpm=50)
print(json.dumps(result))
"
    done
done

echo "Evaluation complete."
