# Reproduction Milestones

**Current: method_runs**

## Progress Log

### [2026-05-20 00:00] - none
- Read the paper's synthetic protocol and audited the existing partial implementation.
- Replaced the fragile method/evaluation scripts with a canonical DQGPM implementation and artifact-based evaluator.
- Prepared a CPU smoke-test job; milestone remains `none` until the job completes successfully.

### [2026-05-20 00:00] - none
- Tightened Algorithm 1 to normalize power-iteration vectors with the dual-number norm described in the paper.
- Removed an undeclared trial-count field from evaluator outputs so `scores.json` mirrors `reference.json`.
- Revalidated `reference.json`, syntax, and import separation before resubmitting the CPU smoke test.

### [2026-05-20 00:00] - method_runs
- CPU smoke job completed successfully: DQGPM and EIG artifacts were generated for `p005_noise005`.
- Artifact-based evaluation wrote valid scores and `validate.py --compare` passed.
- Fixed Algorithm 2 to start DQGPM from the projected spectral initializer, as required by the paper.
- Prepared a larger CPU job over all three declared Table 2 settings to test the core claim.

## Stop Justification
- Not stopped.
