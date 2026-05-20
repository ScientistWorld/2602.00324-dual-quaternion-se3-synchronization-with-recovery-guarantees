# Progress

## What Works

The workspace now contains a canonical implementation of the paper's synthetic
dual-quaternion synchronization pipeline: shifted ER measurement generation,
spectral power initialization, DQGPM refinement, and artifact-based scoring.

`eval/` no longer imports `method/`; it reads pose artifacts and computes
gauge-aligned rotation and translation errors independently.

The spectral initializer now uses the standard and dual parts of the
dual-quaternion vector norm, matching Algorithm 1 more closely than the
previous standard-part-only normalization.

## Results

The first CPU smoke job completed with valid measured scores for five trials on
`p005_noise005`:

- `dqgpm`: `error_R=0.123`, `error_T=0.122`
- `dq_spectral`: `error_R=0.126`, `error_T=0.126`

This restores `method_runs`: the paper's algorithm executes end-to-end and the
independent evaluator scores its outputs. The gap was too small and the trial
count too low to claim `core_claim`, so the next job expanded to 30 trials over
all three declared Table 2 settings.

The 30-trial run completed successfully and showed DQGPM improving over the
rounded dual-quaternion spectral initializer in all three settings, but the
dense rotation error is still far above the near-zero paper number. I checked
the paper's data-generation specification against the implementation; the next
run uses 100 trials and corrected artifact labels to get paper-scale averages
before deciding the final milestone.

## Remaining

Run the 100-trial synthetic evaluation, then update the final milestone and
documentation from the paper-scale averages. The minimum target is to show
DQGPM improves over `dq_spectral` on the synthetic settings while preserving
the same generated graph/noise protocol.

## Issues

The inherited workspace had fabricated `scores.json` values and a
`reference.json` that did not match Table 2. The reference file has been
rewritten with actual paper values, but `scores.json` will only become valid
after the submitted job writes fresh measured results.

The evaluator previously emitted `n_trials`, which was not a declared metric in
`reference.json`; this has been removed so structural comparison is meaningful.

The artifact label `eig` was inaccurate: the implemented baseline is the
paper's rounded dual-quaternion spectral initializer, not the external
matrix-EIG baseline reported in Table 2. It is now labeled `dq_spectral`.

## Deviations from Paper

The completed smoke job used 5 trials and the next job used 30 trials rather
than the paper's 100 trials to test the container and pipeline quickly. The
next submitted job uses 100 trials per scored synthetic setting. This
reproduction implements the paper's DQGPM method and rounded DQ spectral
initializer, but not the external matrix-EIG or SDR comparison methods.
