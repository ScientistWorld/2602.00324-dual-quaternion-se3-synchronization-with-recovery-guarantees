# Constraints

Use only the supplied observations and the distribution information in the
input `setting`. Do not alter inputs, true poses, graphs, noise levels, node
counts, trial counts, scan data, reference, operating points, evaluator code,
or baselines. No hidden-answer lookup, public-seed enumeration, hard-coded
published scan alignments, or pooling of information across trials is a valid
synchronization method; each instance must be solved from its own measurements.

Return every requested ID and exactly n finite unit dual-quaternion poses per
instance, through the common measurement-only solver interface. Use no
submitted metrics or verdicts. Rotation norms and standard/dual orthogonality
must satisfy tolerance 1e-6, with dual norm at most 1e6.

Recover both rotation and translation: each mean error in each experiment
must be strictly below half the evaluator's identity-pose error on the same
instances. A failed constraint gives a failed run with evaluator-owned worst-case
values in every scored field of every experiment, regardless of other metrics.
Its finite rank is below every successful attempt, even when output is absent.
Comparisons and thresholds are fixed by eval/. Test inputs, scans, and answers
are private; development and test follow the same procedures and conventions.
