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
- `eig`: `error_R=0.126`, `error_T=0.126`

This restores `method_runs`: the paper's algorithm executes end-to-end and the
independent evaluator scores its outputs. The gap is too small and the trial
count too low to claim `core_claim`, so the next job expands to 30 trials over
all three declared Table 2 settings.

## Remaining

Analyze the smoke-test output, fix any container or numerical issues, then run
more trials and additional Table 2 settings. The minimum target is to show
DQGPM improves over `eig` on at least the sparse synthetic setting.

## Issues

The inherited workspace had fabricated `scores.json` values and a
`reference.json` that did not match Table 2. The reference file has been
rewritten with actual paper values, but `scores.json` will only become valid
after the submitted job writes fresh measured results.

The evaluator previously emitted `n_trials`, which was not a declared metric in
`reference.json`; this has been removed so structural comparison is meaningful.

The first smoke run exposed a method mismatch: DQGPM was initialized with the
raw scaled power vector, while Algorithm 2 expects a projected UDQ initializer.
The call path now uses the projected spectral initializer.

## Deviations from Paper

The completed smoke job used 5 trials rather than the paper's 100 trials to
test the container and pipeline quickly. The next submitted job uses 30 trials
per setting across the three scored settings. The data model, noise model,
metrics, and algorithms are otherwise kept aligned with the paper's synthetic
protocol.
