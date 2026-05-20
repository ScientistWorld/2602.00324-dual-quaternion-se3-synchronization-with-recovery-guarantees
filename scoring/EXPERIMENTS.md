# Experiments

`p005_noise005` tests the hardest sparse low-noise setting from Table 2. It
checks whether iterative refinement improves stability when only about five
percent of pairwise measurements are observed.

`p005_noise010` keeps the same sparse graph regime and increases both rotation
and translation noise. It measures whether the method preserves its advantage
as measurement corruption grows.

`p030_noise010` uses a denser graph at the mid noise level. It checks the
regime where the spectral baseline is already strong and the proposed method's
gain is expected to be smaller.

Each experiment scores the final feasible poses written by a method artifact.
The included baseline is the rounded spectral initializer for the same
dual-quaternion measurement matrix, not the separate matrix-EIG method from
the paper's comparison table.
