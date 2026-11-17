# Targets

The scored experiments are exactly p005_noise005, p005_noise010,
p008_noise010, p030_noise010, scan_sparse, and scan_dense. Every experiment
reports error_R, error_T, and each quantity's _std, _p90, and _max over
per-trial mean errors. Reduce these scientific recovery errors; matching paper
numbers earns no reward.

Mean accuracy has coefficient magnitude 1 per pose component. Reliability
coefficients are 0.25 for standard deviation, 0.35 for the 90th percentile,
and 0.20 for the maximum. Experiment weights are 0.20, 0.20, 0.15, 0.10, 0.20
and 0.15 respectively. All attempts are ranked by direction-correct,
variance-normalized improvements over the frozen reference. See
briefing/evaluation.md.

Constraint targets are complete valid SE(3) poses and simultaneous recovery of
both components in every experiment (synthetic and real scans). Score metadata
records success/failure and recomputed no-information comparisons. Failures
receive finite worst-case penalties in all 48 scored fields and rank below
every successful attempt.
