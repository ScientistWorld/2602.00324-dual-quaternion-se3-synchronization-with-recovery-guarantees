# Targets

Optimize mean aligned pose-recovery error on the synthetic `SE(3)`
synchronization tasks.

Primary metrics:
- `error_T`: mean translation error after gauge alignment.
- `error_R`: mean rotation error after gauge alignment.

Constraint metrics:
- `error_T_std`: trial-to-trial translation stability.
- `error_R_std`: trial-to-trial rotation stability.

Experiments:
- `p005_noise005`
- `p005_noise010`
- `p030_noise010`

The proposed method should improve over the `eig` spectral baseline under the
same generated graph/noise settings and trial seeds.
