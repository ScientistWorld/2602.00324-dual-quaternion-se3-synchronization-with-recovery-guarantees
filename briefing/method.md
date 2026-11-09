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

## Main Claims

The central empirical claim is that this DQGPM refinement improves pose
recovery over a projected spectral estimator, especially in sparse synthetic
measurement graphs. A secondary claim is that the per-iteration projection
keeps all iterates feasible and produces linear error contraction to a
noise-dependent floor.
