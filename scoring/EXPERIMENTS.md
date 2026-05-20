# Experiments

`p005_noise005` tests the hardest sparse low-noise setting from Table 2. It
checks whether iterative refinement improves stability when only about five
percent of pairwise measurements are observed.

`p005_noise010` keeps the same sparse graph regime and increases both rotation
and translation noise. It measures whether the method preserves its advantage
as measurement corruption grows.

Each experiment scores the final feasible poses written by a method artifact.
The included baseline is the rounded spectral initializer for the same
dual-quaternion measurement matrix, not the separate matrix-EIG method from
the paper's comparison table.

The dense `p030_noise010` setting was run, but its DQGPM translation error was
too far from the paper's reported value to claim as reproduced. It remains a
documented next target rather than part of the current scored gym.
