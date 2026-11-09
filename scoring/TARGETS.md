# Targets

The scored experiments are exactly p005_noise005, p005_noise010,
p008_noise010, and p030_noise010. Every experiment reports error_R, error_T,
and each quantity's _std, _p90, and _max over per-trial mean errors. Reduce
these scientific recovery errors; matching paper numbers earns no reward.

Mean accuracy has coefficient magnitude 1 per pose component. Reliability
coefficients are 0.25 for standard deviation, 0.35 for the 90th percentile,
and 0.20 for the maximum. Weights are 0.30, 0.30, 0.25, and 0.15 respectively.
All attempts are ranked by direction-correct, variance-normalized
improvements over the frozen reference. See briefing/evaluation.md.

Constraint targets are complete valid SE(3) poses and simultaneous recovery of
both components on every experiment. Score metadata records success/failure
and recomputed no-information comparisons. Failures receive finite worst-case
penalties in all 32 scored fields and rank below every successful attempt.
