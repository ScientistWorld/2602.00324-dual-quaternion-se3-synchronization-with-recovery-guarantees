# Targets

Optimize mean aligned pose-recovery error on the synthetic `SE(3)`
synchronization tasks.

Primary metrics:
- `error_T`: mean translation error after gauge alignment.
- `error_R`: mean rotation error after gauge alignment.

Constraint metrics:
- `error_T_std`: trial-to-trial translation stability.
- `error_R_std`: trial-to-trial rotation stability.
- `error_T_p90` and `error_R_p90`: high-percentile recovery error.
- `error_T_max` and `error_R_max`: worst-trial recovery error.

Experiments:
- `p005_noise005`
- `p005_noise010`

A successful submission should reduce aligned pose error and preserve trial
stability under the same generated graph/noise settings and trial seeds. The
less sparse `p008_noise010` and dense `p030_noise010` settings were attempted
during reproduction but are not part of the current scored suite.
