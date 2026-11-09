# Final hardening

The first joint CPU check completed the reference and fixed comparisons but
exhausted the container's temporary filesystem before completing the controls.
Its zero exit code did not establish hardening success. The corrected joint
check will complete the numerical tables from saved raw outputs.

The old test did not consistently reward better science. Stored reference rank
was zero, but rerunning it gave -0.081313, -0.033993, and -0.264303 in the audit
cohort. The stronger noise-aware variant scored +0.496262; the weaker spectral
variant scored -0.122511, a gap smaller than seed noise. These are the report's
old-cohort ranks; new ranks use a different, documented cohort.

All fixes were decided from REDTEAM.md before the joint verification job:

* Private measurement-only inference replaces submission of truth-bearing
  artifacts and public modulo test seeds. The test random family exists only
  in eval/test/. The public 100-member bank is no longer the hidden family.
* Evaluators own fixed reference and baseline implementations, test settings,
  thresholds, no-information poses, and rank specifications. They recompute
  every metric from complete raw poses, reject extra scalar/comparison/truth
  fields, and use no method-written score or flag.
* Duplicate IDs/keys, partial trials, wrong pose counts, nonunit poses, NaN,
  infinity, null, and impossible errors fail. Failed tasks have no rank. Fixed
  comparison entries cannot produce compensation for an unsuccessful task.
* Ranking uses each metric's direction and coefficient magnitude, divided by
  its population variation across successful attempts and the fixed reference.
  Baseline metrics do not enter a candidate's improvement sum.
* The actual two-stage paper procedure is retained. The matrix EIG comparison
  now uses the source method's homogeneous-row least-squares/nullspace rounding
  (https://fusiello.github.io/papers/siims16.pdf, sections 2.2-2.3). Its connected
  component extension uses no truth; isolated nodes receive identity poses.
* The incomplete check exposed an arbitrary translation origin in the power
  initializer. Reference and baseline output serialization now choose zero
  mean body-frame translation by one common right translation. This preserves
  every relative pose and every algorithm iterate; it prevents a random origin
  amplifying noisy rotations in the paper's translation alignment. The joint
  check verifies relative-pose invariance and checks the matrix baseline too.
* Test sizes rise from 57 selected trials to 200/200/150/100 independent trials,
  at the original n=100. Public evaluation uses 100 per setting. Initializer
  seeds are fixed, and seed controls and all variants see the same instances.
* Added p=0.08 and p=0.30 noisy settings from the paper. Sparse settings retain
  60% weight; added settings receive 25% and 15%. This tests noise handling
  beyond sparse-graph ambiguity and reduces the influence of unidentifiable
  isolated poses. Per-metric coefficient magnitudes are unchanged.

No reference metric was at its zero bound in the old report. The added
experiments extend the paper's noise/density study, rather than merely adding
a saturated task. The stronger variant must have positive paired rank
confidence bounds, the weaker spectral variant negative bounds, and the
stronger gain must exceed the observed reference-seed rank range.

The paper's Table 2 values remain unchanged under `_paper_reported` in
scoring/reference.json. Its 15% trimmed statistics are not numeric targets for
this gym's untrimmed trials and tail metrics. Final numeric gym references are
measured from the final implementation, without selecting seeds to match a
paper value. Historical milestone entries describing a modulo split are
superseded by this independent hidden family.

The audit retains attacks that enumerate visible answers, replace truth,
return one pose, select trials, substitute easier data, forge baselines,
compensate total task failure, or return NaN/negative scalars. Before/after
ranks and paired uncertainty will be recorded from the joint check. Existing
empty/null/constant defenses are preserved; unchanged old attack scripts are
not rerun. Runtime answers and per-trial details remain in eval/test/.cache/;
only aggregate audit statistics are published.

No defenses are added against leftover processes or Python environment
modification: evaluation runs in a fresh container. General numerical search
on observed data is permitted; exhaustive lookup of the old public family is
not. Finite synthetic trials cannot establish theoretical recovery guarantees,
and this package does not reproduce SDR, real scan registration, or runtime
speed claims. These limitations are not scored targets.

The temporary-file failure is repaired by keeping one experiment's solver
files inside its evaluator cache, removing them immediately after reading raw
output, and treating evaluator I/O errors as job failures. An incomplete audit
or failed scientific assertion now stops packaging. No shortcut is considered
closed merely because its solver encountered an infrastructure failure.
