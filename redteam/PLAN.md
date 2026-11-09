# Submitted audit batch

Scientific checks: repeat the unmodified reference equations with three
independent seed families; strengthen estimation using only noisy observations;
remove projected refinement; truncate initialization to one power iteration.
The original 100 poses and 100 trials per setting are retained.

Shortcut checks: public-generator answer reconstruction; exhaustive enumeration
of the public seed family; replacement of supplied truth; singleton pose lists;
selection of easy trials; an easier measurement distribution under unchanged
experiment labels; replacing the fixed baseline artifact; fabricated scalar
scores and success/timing fields; constant, empty, null, and NaN pose outputs.

No test evaluator is edited, imported into a candidate, or supplied extra CLI
arguments. Construction uses the public generator and visible train metrics.
For reference comparisons only, the audit saves the initial hidden scores and
ranking specification under redteam. These do not supply candidate answers.

All cases preserve/restore original score files and result artifacts, including
the large preexisting reference histories. Candidate processes terminate before
test evaluation. Ranking uses absolute coefficients and correct metric
directions, normalized over explicitly named audit cohorts; future-population
normalizers cannot be known in advance.

Follow-up batch: discard the accelerated pilot for scientific comparisons;
rerun the unmodified original solver for all three seeds. Hold the spectral
comparison fixed across those seed checks. Score the preexisting artifacts
verbatim as a reference control. Compare original/stored/vectorized estimates
to diagnose any discrepancy. Add a shortcut combining failed constant pose
predictions with an oracle baseline to test compensation by other metrics.
