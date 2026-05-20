# Overview

This paper studies synchronization over `SE(3)`: recovering absolute 3D poses
from noisy relative transformations. The reproduction implements the paper's
unit-dual-quaternion pipeline: spectral power initialization followed by
DQGPM refinement with elementwise projection onto valid poses.

The packaged benchmark focuses on the synthetic experiments from Table 2,
where DQGPM is compared against the projected spectral estimator under sparse
and dense Erdos-Renyi observation graphs.
