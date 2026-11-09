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

A final packaging job will rescore saved raw poses into reference-only
canonical files, verify consistency, and run python3 validate.py in default,
post-design, and post-reproducer modes. Verification is pending that job.
The first joint job's temporary-storage failure is not treated as evidence.
Unrelated pre-existing root-system-file and trajectory changes remain untouched.
