# Data Interface

The scored benchmark is synthetic and does not require external downloads.

`data/synthetic.py` provides a method-independent generator for the fixed
`SE(3)` synchronization instances used by the gym. It exposes the experiment
settings, ground-truth poses, and noisy relative-pose measurements without
importing from `method/`, so from-scratch agents can build their own solvers
against the same problem inputs.

Evaluation expects method artifacts to contain one estimated pose per node for
each trial, using records with `q_st` and `q_dual` arrays for the pose
representation. The evaluator only uses these records to recover rotations and
translations for gauge-aligned scoring.
