# Final gym design

The final protocol uses measurement-only solver commands, private instances at
test time, and independent public instances from the same distribution. A
method returns complete raw poses; evaluators fix all comparisons and
recompute every scientific quantity. Constraints precede rank arithmetic.

The n=100 problems cover four density/noise settings. Enlarged paired tests
and fixed initializer seeds address the seed-noise problem identified by the
red-team audit. The complete joint audit reruns all affected solvers together; final packaging
rescores those raw outputs. See
HARDENING.md for before/after results, uncertainty, fixes, and limitations.

Historical public-seed splits and truth-bearing result artifacts are no longer
accepted. Paper trimmed statistics are preserved as context, while the gym
scores untrimmed error and reliability. Evaluator-owned references are frozen
source snapshots, with no runtime imports from method/ or between slices.

The audit establishes stronger/weaker ordering and improvement over the DQ
initializer. It does not establish uniform superiority over matrix EIG. The
comparison is retained, with no coefficient changes to manufacture an advantage.
