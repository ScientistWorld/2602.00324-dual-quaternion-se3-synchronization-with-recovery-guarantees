# Interface and measurement

Run `bash scripts/evaluate_train.sh` for public development and
`bash scripts/evaluate_test.sh` for hidden evaluation. Both take no arguments
and discover `method/solver.json` plus every `methods/*/solver.json`. A manifest
has a unique `name` and a `command` array, such as
`{"name":"candidate","command":["python3","-m","method.solve"]}`.
The names `dq_spectral`, `matrix_eig`, `sdr`, and `_reference`, and the prefix
`invalid_manifest_`, are reserved.

Each command receives `--input PATH --output PATH` once per experiment. Input
JSON has `format` (`se3-sync-measurements/v1`), `experiment`, `setting`, and
`instances`. `setting` has `source` (`synthetic` or `stanford_scans`),
`graph`, `measurement_model` (`additive` or `rigid_perturbation`), `sigma_t`
and `sigma_r_deg`, plus `n` and `p` for synthetic settings. Each instance has
an opaque `id`, `n`, `edges` (observed pairs i<j), `q_st`, and `q_dual` (one
scalar-first four-vector per edge). Reverse observations are conjugates;
diagonal entries are identities. No hidden seed or answer is provided. Return
only `{"estimates":{"ID":{"q_st":[[...],...],"q_dual":[[...],...]},...}}`.
Every input ID must occur exactly once, with exactly n poses. Metadata,
submitted scores, baselines, alternate truth, partial trials, and duplicate JSON
keys are not accepted. Non-finite values, nonnumeric values, and nonunit poses
fail the attempt. Unit tolerances are 1e-6 for rotation norm and the standard/
dual inner product; dual norm must not exceed 1e6.

Synthetic experiments (n=100, graphs conditioned on connectivity): p=0.05 with
translation/rotation noise standard deviations (0.05, 5 degrees) and
(0.10, 10 degrees); p=0.08 and p=0.30 with (0.10, 10 degrees). A measurement
is `x_i x_j^* + xi_ij - 1` for a random unit dual quaternion `xi_ij` with
the stated rotation-angle and translation spread. Public evaluation has 100
trials per setting; hidden evaluation has 200, 200, 150, and 100.

Scan experiments: `scan_sparse` and `scan_dense`. Each measurement is a
pairwise ICP registration of two scans, right-multiplied by a random rigid
motion (angle ~ N(0, 1 degree) about a uniform axis, translation ~ N(0, 1 mm)
per axis); translations are in meters. Every trial applies a fresh unknown
rigid frame to each scan and relabels the scans. Public evaluation uses four
scan sets (60 trials each per graph type); hidden evaluation uses four other
sets for sparse and three for dense graphs (100 trials each). Instances are
shared by all methods in an evaluation. Public and hidden random families are
independent.

Each trial removes the estimate's mean body-frame translation and then fits
one global right gauge: the rotation is the quaternion average of
`q^_j* q_j` with signs resolved by the dominant eigenvector of their scatter
matrix, and the translation is the least-squares shift. Quaternion
double-cover signs never affect the score. Rotation error is
`2 acos(2 <q1,q2>^2 - 1)` (range 0 to 2 pi, the paper's convention).
Translation error is Euclidean distance after alignment. Each trial averages
all nodes. Metrics are the untrimmed mean, population standard deviation,
90th percentile (linear interpolation), and maximum of those trial averages,
separately for rotation and translation. Lower is better for all eight.

The evaluator fixes the inputs, true poses, comparison solvers, reference,
and task thresholds. If either mean error in any experiment reaches half that
of the fixed identity-pose estimate on the same instances, the attempt fails.
Invalid or failed attempts receive finite worst-case penalties in every
metric of every experiment, including when no output or manifest is usable.
The evaluator bounds any passing attempt's statistics from its nonnegative
trial errors, trial count, and mean-error thresholds, then places each penalty
strictly above that bound. Penalties are marked failures, not measured errors.
Their finite ranks are below every successful attempt; other metrics cannot
compensate. Measured errors before failure remain separate diagnostics.

Rank is the sum over experiments and metrics of
`weight * abs(coefficient) * direction * (value-reference) / population_std`.
Direction is +1 for higher-is-better metrics and -1 otherwise. The scale is
computed across all candidate attempts on disk and the frozen reference;
evaluator-owned baselines do not enter this population. An exactly constant
metric contributes zero. Adding attempts changes numerical rank scales, so
ranks from different cohorts are not numerically comparable. Failure penalties
are assigned before this arithmetic. `scoring/reference.json` defines
coefficients and weights, with identical fixed evaluator snapshots.

The evaluator saves raw outputs in its own slice cache. `--reuse-outputs`
recomputes every metric from those poses, checking the exact input fingerprint;
it never imports a method's score or verdict. Default evaluation always runs
all discovered solvers. Hidden raw poses, inputs, scans, and per-trial errors
remain inside eval/test/. Neither evaluation slice imports the other or
method/. Score metadata also lists per-object mean errors for the scan
experiments (diagnostic only).
