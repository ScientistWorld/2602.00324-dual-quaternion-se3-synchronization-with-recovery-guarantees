# Experiments

`p005_noise005` tests the hardest sparse low-noise setting from Table 2. It
checks whether a synchronization method remains accurate and stable when only
about five percent of pairwise measurements are observed.

`p005_noise010` keeps the same sparse graph regime and increases both rotation
and translation noise. It measures whether a method preserves low recovery
error as measurement corruption grows.

Each experiment scores the final feasible poses written by a method artifact.
The artifact must provide one estimated rigid pose per node for every scored
trial.

The `p008_noise010` and `p030_noise010` settings were attempted during
reproduction but are not part of the current scored gym. They remain natural
next targets for expanding benchmark coverage.
