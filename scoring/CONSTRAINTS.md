# Constraints

Use only the supplied observations and public distribution information. Do not
alter inputs, true poses, graph density, noise level, node count, trial count,
reference, operating points, evaluator code, or baselines. No hidden-answer
lookup or public-seed enumeration is a valid synchronization method.

Return every requested ID and exactly 100 finite unit dual-quaternion poses
per instance, through the common measurement-only solver interface. Use no
submitted metrics or verdicts. Rotation norms and standard/dual orthogonality
must satisfy tolerance 1e-6, with dual norm at most 1e6.

Recover both rotation and translation: each mean error in each experiment
must be strictly below half the evaluator's identity-pose error on the same
instances. A failed constraint gives a failed run with evaluator-owned worst-case
values in every scored field of every experiment, regardless of other metrics.
Its finite rank is below every successful attempt, even when output is absent.
Comparisons and thresholds are fixed by eval/. Test inputs and answers are
private; development and test have matching distributions and conventions.
