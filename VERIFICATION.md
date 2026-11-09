# Verification status

Job `00902d7f-40f` completed the full numerical audit from final solver code.
Protocol validation, vectorized-algorithm equivalence, translation-origin
invariance, honest stronger/weaker ordering, seed controls, and all repaired
shortcuts passed. Stronger hidden rank was +8.488435, weaker spectral rank
-1.342277, with paired intervals separated from zero and from seed variation.

The job exited 1 because the paper's uniform advantage over matrix EIG was
not established. That negative result is retained in HARDENING.md and the
aggregate audit report. No comparator, coefficient, or solver was changed to
make the assertion pass. The supported reproduction scope is pose recovery
and improvement over the rounded DQ initializer, not the complete paper.

Final packaging job `40fcc388-e69` exited 0. It rescored saved raw poses into
canonical files containing only the reference and two fixed baselines, froze
the measured gym-scale targets, and verified exact agreement with the final
raw-output audit. Both slices contain four experiments and all three methods
are valid. Paper-reported values remain unchanged under `_paper_reported`.
The post-design and post-reproducer validator modes passed, including the
default structural checks. The separate artifact verifier records
`verified_with_unresolved_comparison` and `all_requested_conditions_met: false`.

The validator emitted three heuristic warnings about random-number generation
in evaluator files. The test generator creates private inputs, fixed
comparators run inference, and candidate scores are recomputed from raw pose
outputs; these warnings do not indicate training or an ignored candidate.
`scripts/run.sh` again runs the full reference reproduction without depending
on audit controls or saved caches.

The first joint job's temporary-storage failure is not treated as evidence.
Unrelated pre-existing root-system-file and trajectory changes remain untouched.
