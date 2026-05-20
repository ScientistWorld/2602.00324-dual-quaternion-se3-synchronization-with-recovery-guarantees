# Constraints

Future methods must use the same synthetic data protocol, trial seeds, graph
probabilities, noise levels, and `n=100` problem size when comparing scores.

Methods must output one valid `SE(3)` pose per node in the JSON artifact format
accepted by `scripts/evaluate.sh`. Evaluation must remain gauge-aligned and
must not use ground truth except for scoring.

Changing the observation rate, reducing the noise, increasing the number of
measurements, or evaluating on easier synthetic data is not a valid
improvement.
