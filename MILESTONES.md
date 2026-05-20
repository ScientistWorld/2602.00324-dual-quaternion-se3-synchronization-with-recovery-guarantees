# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-05-20 05:46] - core_claim
- Implemented the paper's two-stage dual-quaternion SE(3) synchronization pipeline: spectral power initialization followed by DQGPM projection iterations.
- Ran the synthetic sparse Table 2 settings with 100 trials and artifact-based evaluation.
- DQGPM improves over the rounded dual-quaternion spectral initializer on both scored sparse settings, supporting the central refinement claim at reduced reproduction scope.

### [2026-05-20 06:10] - core_claim
- Audited the continuation workspace and restored `core_claim`: the implementation is the paper's dual-quaternion spectral initializer plus DQGPM, evaluation is independent, and post-reproducer validation passes.
- Added the `p008_noise010` Table 2 setting to the planned scored suite for a follow-up CPU job; milestone remains `core_claim` until that job completes.

### [2026-05-20 06:25] - core_claim
- Reviewed job `a5472b1a-918`: the `p008_noise010` extension ran and DQGPM improved over `dq_spectral`, but post-reproducer validation rejected the absolute translation error (`0.152492` vs paper `0.064`).
- Removed `p008_noise010` from the claimed scored suite and documented it as an attempted, unreproduced extension. The validated two-setting sparse suite remains the current `core_claim`.

## Stop Justification
- Completed at milestone `core_claim`.
