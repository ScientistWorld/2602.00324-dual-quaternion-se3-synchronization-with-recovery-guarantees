# Scored experiments

All experiments ask whether every absolute pose can be recovered from noisy
pairwise observations, up to a single global right gauge. They measure mean
rotation and translation error and the variability, 90th percentile, and
maximum of per-trial mean errors. All are lower-is-better. Accuracy is useful
only when both pose components are recovered and every output is valid.

| Experiment | Observed pair probability | Translation noise | Rotation noise | Weight | Public / hidden trials |
|---|---:|---:|---:|---:|---:|
| p005_noise005 | 0.05 | 0.05 | 5 degrees | 0.30 | 100 / 200 |
| p005_noise010 | 0.05 | 0.10 | 10 degrees | 0.30 | 100 / 200 |
| p008_noise010 | 0.08 | 0.10 | 10 degrees | 0.25 | 100 / 150 |
| p030_noise010 | 0.30 | 0.10 | 10 degrees | 0.15 | 100 / 100 |

The first two settings measure recovery with few observations and the cost of
increased measurement noise. The third tests whether additional observations
improve recovery without concealing poorly observed poses. The fourth tests
accuracy when most poses have many observations, separating measurement-noise
handling from sparse-graph failures. All retain 100 nodes and the same
observation model. None discards outlying trials or disconnected graphs.

There is a hard constraint on task success: in every setting, both mean errors
must remain below half the error of a fixed no-information estimate. All poses
and trial IDs must also be valid and complete. These constraints are recomputed
from raw outputs and recorded in score metadata. Failed attempts are unranked.

The scored statistics describe recovery, not agreement with a reported number.
Paper-reported trimmed statistics are historical context under `_paper_reported`
in reference.json. The final gym's untrimmed reference measurements are stored
separately as numeric results. Fixed baselines use the identical inputs and
alignment. The hidden evaluator does not train any method.
