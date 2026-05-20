# Progress

## What Works

The workspace now contains a canonical implementation of the paper's synthetic
dual-quaternion synchronization pipeline: shifted ER measurement generation,
spectral power initialization, DQGPM refinement, and artifact-based scoring.

`eval/` no longer imports `method/`; it reads pose artifacts and computes
gauge-aligned rotation and translation errors independently.

## Results

No verified reproduced scores yet in this turn. A CPU test job is being
submitted to run `p005_noise005` for DQGPM and the projected spectral baseline.

## Remaining

Analyze the smoke-test output, fix any container or numerical issues, then run
more trials and additional Table 2 settings. The minimum target is to show
DQGPM improves over `eig` on at least the sparse synthetic setting.

## Issues

The inherited workspace had fabricated `scores.json` values and a
`reference.json` that did not match Table 2. The reference file has been
rewritten with actual paper values, but `scores.json` will only become valid
after the submitted job writes fresh measured results.

## Deviations from Paper

The first submitted job uses 5 trials rather than the paper's 100 trials so the
container and algorithm can be smoke-tested quickly on a CPU test node. The
data model, noise model, metrics, and algorithms are otherwise kept aligned
with the paper's synthetic protocol.
