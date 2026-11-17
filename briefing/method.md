# Paper's Method

## Key Contribution

The paper formulates `SE(3)` synchronization directly over unit dual
quaternions and uses a two-stage solver with recovery guarantees.

## Approach

Each pose is represented as a unit dual quaternion
`x = (1 + eps * t / 2) q`. Pairwise relative measurements form a Hermitian
dual-quaternion matrix `C`. The objective maximizes `x* C x` over one unit
dual quaternion per node.

The solver first runs power iteration on the Hermitian dual-quaternion
measurement matrix to obtain a spectral initializer. It then applies the dual
quaternion generalized power method: repeatedly compute `y = C x` and project
each entry of `y` onto the unit dual-quaternion set.

When writing poses, the implementation fixes the free translation origin by
one common right translation that makes the mean body-frame translation zero.
All relative poses and all algorithm iterates are preserved. This output
convention removes the initializer's arbitrary translation gauge before the
paper's error alignment; the baselines use the same convention.

The method needs measurements whose dual-quaternion signs are consistent with
one choice of node representatives (the model `C = x x^* + noise`); the scan
experiments supply relative poses in that lifted form.

## Main Claims

The paper claims accurate and stable recovery, improvement during projected
refinement, uniform superiority over matrix EIG in its synthetic study, and
on real scan registration accuracy comparable to the best of EIG and SDR at
lower cost than SDR (with EIG and SDR failing on sparse scan graphs).
The reproduction verifies refinement over the rounded DQ initializer and
recovery of both pose components on synthetic and real-scan graphs, with
accuracy comparable to SDR and EIG on real scans. It does not reproduce
superiority over matrix EIG (the two tie on connected graphs) nor the
failures of EIG and SDR on sparse scan graphs; SDR is slightly more accurate.
Runtime is not scored. Theoretical recovery guarantees and linear convergence
rates are not established by this finite empirical suite.
