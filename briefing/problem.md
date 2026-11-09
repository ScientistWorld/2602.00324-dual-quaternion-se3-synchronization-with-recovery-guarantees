# Recover rigid poses from noisy pairwise measurements

Estimate one rotation and translation for each of 100 nodes. An observed edge
represents the relative pose of its two endpoints, with additive noise in the
provided scalar-first dual-quaternion coordinates. Unobserved edges contain no
information. The input specifies the noise distribution and graph density.

Every returned pose must be a valid element of SE(3). The evaluation removes
one global right gauge and measures errors against unavailable true poses.
Disconnected components receive no additional gauge freedom: their relative
placement is unidentifiable and remains a source of error. Methods should
handle uncertainty rather than remove difficult nodes or trials.

Public development instances and hidden instances follow the same distribution
and have the same problem size. Success means improving both mean recovery
accuracy and reliability while preserving valid poses and recovering both
rotation and translation on every setting.
