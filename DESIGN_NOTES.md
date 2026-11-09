# Final gym design

The final protocol uses measurement-only solver commands, private instances at
test time, and independent public instances from the same distribution. A
method returns complete raw poses; evaluators fix all comparisons and
recompute every scientific quantity. Constraints precede rank arithmetic.

The n=100 problems cover four density/noise settings. Enlarged paired tests
and fixed initializer seeds address the seed-noise problem identified by the
red-team audit. All patches are checked together in one compute job. See
HARDENING.md for before/after results, uncertainty, fixes, and limitations.

Historical public-seed splits and truth-bearing result artifacts are no longer
accepted. Paper trimmed statistics are preserved as context, while the gym
scores untrimmed error and reliability. Evaluator-owned references are frozen
source snapshots, with no runtime imports from method/ or between slices.
