# Scored experiments

All experiments ask whether every absolute pose can be recovered from noisy
pairwise observations, up to a single global gauge. They measure mean
rotation and translation error and the variability, 90th percentile, and
maximum of per-trial mean errors. All are lower-is-better. Accuracy is useful
only when both pose components are recovered and every output is valid.

| Experiment | Data | Graph | Noise (translation, rotation) | Weight | Public / hidden trials |
|---|---|---|---|---:|---:|
| p005_noise005 | synthetic, 100 nodes | p=0.05, connected | 0.05, 5 degrees | 0.20 | 100 / 200 |
| p005_noise010 | synthetic, 100 nodes | p=0.05, connected | 0.10, 10 degrees | 0.20 | 100 / 200 |
| p008_noise010 | synthetic, 100 nodes | p=0.08, connected | 0.10, 10 degrees | 0.15 | 100 / 150 |
| p030_noise010 | synthetic, 100 nodes | p=0.30, connected | 0.10, 10 degrees | 0.10 | 100 / 100 |
| scan_sparse | Stanford range scans, 10-15 per object | pairs registered without pose prior | 1 mm, 1 degree | 0.20 | 240 / 400 |
| scan_dense | Stanford range scans, 12-15 per object | pairs registered from a turntable prior | 1 mm, 1 degree | 0.15 | 240 / 300 |

The first two synthetic settings measure recovery with few observations and
the cost of increased measurement noise. The third tests whether additional
observations improve recovery. The fourth tests accuracy when most poses have
many observations, separating noise handling from sparse-graph effects.
Synthetic graphs are always connected, so every pose is identifiable.

The two scan experiments measure the same task on real multi-view registration
problems, where measurements also carry real pairwise-registration error and
graphs have the structure of real scanning sessions. The sparse graphs keep few
pairs per scan, the dense graphs most overlapping pairs. Hidden scan objects
(bunny, Buddha, dragon, Armadillo in their standing scan sets) differ from the
public ones (Buddha and dragon scanned on their side, back, or upright).
Absolute frames and node order are randomized in every trial.

There is a hard constraint on task success: in every experiment, both mean
errors must remain below half the error of a fixed no-information estimate.
All poses and trial IDs must also be valid and complete. These constraints are
recomputed from raw outputs and recorded in score metadata. Failed attempts
receive finite worst-case penalties in every scored field of every experiment
and rank below every successful attempt.

The scored statistics describe recovery, not agreement with a reported number.
Paper-reported values are historical context under keys starting with `_` in
reference.json. Fixed comparison methods use the identical inputs and
alignment. The hidden evaluator does not train any method.

The reference improves both mean errors over the simple development baseline
in all experiments. A matrix spectral comparison ties the reference, and a
semidefinite-relaxation comparison (scan experiments only) is slightly more
accurate on the scans. The scan experiments therefore leave only a few
percent of room above the reference; the synthetic experiments leave much
more. HARDENING.md records these comparisons and the headroom controls.
