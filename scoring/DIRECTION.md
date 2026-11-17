# Direction

Improve SE(3) synchronization from incomplete, noisy relative observations,
on synthetic graphs and on real multi-view scan registration graphs.
Explore estimation, noise modeling, weighting, optimization, and uncertainty
handling while preserving the common inputs and complete valid-pose output
interface. Improve accuracy without sacrificing recovery of either pose
component or reliability on difficult instances. Lower values are better for
every scored metric. Numerical rank coefficients use their magnitude,
independent of sign.

Develop on the public distribution and evaluate on unseen hidden instances
and unseen scan objects. Methods may learn from public data, but must not
reconstruct the hidden random family, consult answers, forge comparisons, or
change the task. General-purpose optimization of the observed objective is an
honest alternative and may expose scientific headroom; it is not a license to
optimize against hidden truth.
