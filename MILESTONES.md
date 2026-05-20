# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-05-20 05:46] - core_claim
- Implemented the paper's two-stage dual-quaternion SE(3) synchronization pipeline: spectral power initialization followed by DQGPM projection iterations.
- Ran the synthetic sparse Table 2 settings with 100 trials and artifact-based evaluation.
- DQGPM improves over the rounded dual-quaternion spectral initializer on both scored sparse settings, supporting the central refinement claim at reduced reproduction scope.

## Stop Justification
- Completed at milestone `core_claim`.
- Higher milestones remain open because the external matrix-EIG/SDR baselines and real point-cloud registration experiments are not implemented, and the dense synthetic setting remains numerically outside the accepted reproduction range.
