# Recover rigid poses from noisy pairwise measurements

Estimate one rotation and translation for each node of a measurement graph.
An observed edge carries a noisy relative pose of its two endpoints in
scalar-first dual-quaternion coordinates; unobserved edges carry no
information. The input states the graph source, the measurement model, and
the noise levels.

Two families of problems are scored:

* Synthetic graphs with 100 nodes, uniformly random poses (translations of unit
  scale), random observation graphs that are always connected, and additive
  noise on the dual-quaternion entries. Four density/noise settings.
* Real multi-view registration: range scans of objects from the Stanford 3D
  Scanning Repository, 10 to 15 scans per object. Each observed edge is a
  pairwise registration (iterative closest point) between two scans, further
  perturbed by a random rigid motion with the stated noise levels. "Sparse"
  graphs keep only pairs registered without any pose prior; "dense" graphs use
  pairs registered from a turntable-angle prior. True poses come from the
  repository's own alignment, so measurements also contain real registration
  error. Every trial expresses each scan in an unknown rigid coordinate frame
  and in a random order, so absolute poses carry no prior structure.

Measurement quaternion signs are consistent with one fixed (unknown) choice of
node representatives, as in a model `C_ij = x_i x_j^* + noise`.

Every returned pose must be a valid element of SE(3). The evaluation removes
one global gauge and measures errors against unavailable true poses. Public
development instances and hidden instances follow the same procedures; the
hidden scan experiments use different objects than the public ones. Success
means improving mean recovery accuracy and reliability while preserving valid
poses and recovering both rotation and translation in every experiment.
