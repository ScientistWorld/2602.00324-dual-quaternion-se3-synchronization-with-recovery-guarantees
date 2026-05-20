# Evaluation

## Metrics

Evaluation first aligns the estimated poses to the ground truth by a single
global right action. Rotation error is
`2 arccos(2 <q1, q2>^2 - 1)` for unit quaternions. Translation error is the
Euclidean norm between aligned translations. `error_R` and `error_T` are means
over all poses and are lower-is-better. Standard deviations are reported over
independent trials.

## Targets

The benchmark target is low gauge-aligned rotation and translation error on
synthetic pose synchronization instances with fixed graph density, noise level,
problem size, and trial seeds. The currently scored paper reference targets are
from the synthetic `n=100` results table:

- `p005_noise005`: `p=0.05`, `sigma_t=0.05`, `sigma_r=5 deg`.
- `p005_noise010`: `p=0.05`, `sigma_t=0.10`, `sigma_r=10 deg`.

Current reproduced scores cover the two sparse `p=0.05` settings. Additional
settings, including denser graphs such as `p=0.08` and `p=0.30`, are possible
extensions but are not part of the current scored suite.

## Evaluation Protocol

Generate an Erdos-Renyi measurement graph with observation probability `p`.
Ground-truth rotations use random axes and angles uniform in `[0, 2pi)`;
translations have iid `N(0,1)` coordinates. Noise rotations use random axes
and Gaussian angles with standard deviation `sigma_r` degrees; noise
translations have iid `N(0, sigma_t^2)` coordinates. Each observed edge stores
a noisy relative rigid transformation from one node to another; missing
off-diagonal edges are unobserved. Results are averaged across trials.

The method-independent generator in `data/synthetic.py` exposes these fixed
settings and measurement records for future solvers.
