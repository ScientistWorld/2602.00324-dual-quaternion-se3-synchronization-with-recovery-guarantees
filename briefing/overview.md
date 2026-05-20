# Overview

This paper studies synchronization over `SE(3)`: recovering absolute 3D poses
from noisy relative transformations. The reproduction implements the paper's
unit-dual-quaternion pipeline: spectral power initialization followed by
DQGPM refinement with elementwise projection onto valid poses.

The packaged benchmark focuses on synthetic experiments from Table 2 in sparse
and moderately sparse graph regimes. It scores DQGPM against the rounded
dual-quaternion spectral initializer on the same generated measurement
artifacts. The paper's external matrix-EIG/SDR baselines, dense synthetic
setting, and real point-cloud registration experiments remain documented
targets for extending the gym.
