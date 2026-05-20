# Evaluation

## Metrics

Evaluation first aligns the estimated poses to the ground truth by a single
global right action. Rotation error is
`2 arccos(2 <q1, q2>^2 - 1)` for unit quaternions. Translation error is the
Euclidean norm between aligned translations. `error_R` and `error_T` are means
over all poses and are lower-is-better. Standard deviations are reported over
independent trials.

## Baselines and Targets

The paper compares DQGPM against external matrix-based EIG and SDR methods.
This reproduction implements the paper's DQGPM method and uses
`dq_spectral`, the rounded dual-quaternion spectral initializer, as the
implemented benchmark-local baseline. The central target is that `dqgpm`
reduces aligned pose error after iterative refinement while preserving the same
measurement protocol. Paper reference targets are from synthetic Table 2 for
`n=100`:

- `p005_noise005`: `p=0.05`, `sigma_t=0.05`, `sigma_r=5 deg`.
- `p005_noise010`: `p=0.05`, `sigma_t=0.10`, `sigma_r=10 deg`.
- `p008_noise010`: `p=0.08`, `sigma_t=0.10`, `sigma_r=10 deg`.
- `p030_noise010`: `p=0.30`, `sigma_t=0.10`, `sigma_r=10 deg`.

Current reproduced scores cover sparse and moderately sparse settings. The
dense `p030_noise010` reference remains documented as an unreproduced target
because the measured translation error was outside the accepted reproduction
range.

## Evaluation Protocol

Generate an Erdos-Renyi measurement graph with observation probability `p`.
Ground-truth rotations use random axes and angles uniform in `[0, 2pi)`;
translations have iid `N(0,1)` coordinates. Noise rotations use random axes
and Gaussian angles with standard deviation `sigma_r` degrees; noise
translations have iid `N(0, sigma_t^2)` coordinates. The shifted noisy edge
model is `C_ij = x_i x_j* + xi_ij - 1`, diagonal entries are identity, and
missing off-diagonal entries are zero. Results are averaged across trials.
