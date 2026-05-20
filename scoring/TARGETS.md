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
- `p008_noise010`

The proposed method should improve over the `dq_spectral` rounded
dual-quaternion spectral initializer under the same generated graph/noise
settings and trial seeds. The `p008_noise010` setting expands the scored suite
to a less sparse graph from Table 2. The dense `p030_noise010` run is left in
`reference.json` as a paper target, but it is not claimed in `scores.json`
because the reproduced translation error was outside the validator's accepted
magnitude range. The paper's reported matrix-EIG baseline also remains in
`reference.json`, but this reproduction does not currently implement that
external baseline.
