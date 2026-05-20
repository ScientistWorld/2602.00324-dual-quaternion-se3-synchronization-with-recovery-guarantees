# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-05-20 06:38] - core_claim
- Continued verifier audit of the packaged reproduction.
- Corrected the `p005_noise005` paper reference translation error from Table 2 (`0.069 ± 0.043`) and updated target docs to include the declared p90/max stability metrics.
- Submitting a CPU validation job to refresh `scores.json` from existing artifacts with the full metric set and rerun post-reproducer validation inside the container.

### [2026-05-20 06:12] - core_claim
- Reviewed compute job `b6338986-caa`: it regenerated the two retained 100-trial sparse synthetic experiments, scored method and baseline artifacts, and exited successfully.
- `validate.py --compare --post-reproducer` passed inside the container, including score consistency, import separation, artifact-based evaluation, and shared-path checks.
- Restored `core_claim`: DQGPM improves over the rounded dual-quaternion spectral initializer on both retained sparse Table 2 settings while preserving the paper's dual-quaternion measurement, initialization, and projection-refinement pipeline.

### [2026-05-20 06:10] - method_runs
- Continuing from a prior `core_claim` claim with the milestone reset to `method_runs` as required.
- Audited the implementation: the code contains the paper's dual-quaternion shifted measurement model, spectral power initializer, and projected DQGPM refinement rather than a surrogate.
- Preparing a fresh CPU validation job before restoring `core_claim`.

### [2026-05-20 06:02] - core_claim
- Implemented and packaged the paper's dual-quaternion spectral initializer plus DQGPM refinement for synthetic SE(3) synchronization.
- Ran 100-trial CPU jobs on two sparse Table 2 settings and scored outputs with an evaluator that reads artifacts without importing `method/`.
- DQGPM improves over the rounded dual-quaternion spectral initializer on rotation and translation errors in both retained settings, while absolute errors remain worse than the paper's reported values.

## Stop Justification
- Completed at milestone `core_claim`.
