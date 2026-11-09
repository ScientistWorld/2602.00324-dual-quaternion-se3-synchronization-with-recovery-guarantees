# Interface and measurement

Run `bash scripts/evaluate_train.sh` for public development and
`bash scripts/evaluate_test.sh` for hidden evaluation. Both take no arguments
and discover `method/solver.json` plus every `methods/*/solver.json`. A manifest
has a unique `name` and a `command` array, such as
`{"name":"candidate","command":["python3","-m","method.solve"]}`.
The names `dq_spectral`, `matrix_eig`, and `_reference` are reserved.

Each command receives `--input PATH --output PATH`. Input JSON has `format`
(`se3-sync-measurements/v1`), `experiment`, `setting`, and `instances`. Each
instance has an opaque `id`, `n`, `edges` (observed pairs i<j), `q_st`, and
`q_dual` (one scalar-first four-vector per edge). Reverse observations are
conjugates; diagonal entries are identities. No hidden seed or answer is
provided. Return only
`{"estimates":{"ID":{"q_st":[[...],...],"q_dual":[[...],...]},...}}`.
Every input ID must occur exactly once, with exactly n poses. Metadata,
submitted scores, baselines, alternate truth, partial trials, and duplicate JSON
keys are not accepted. Non-finite values, nonnumeric values, and nonunit poses
fail the attempt. Unit tolerances are 1e-6 for rotation norm and the standard/
dual inner product; dual norm must not exceed 1e6.

All settings have n=100. The two p=0.05 settings have translation/rotation noise
standard deviations (0.05,5 degrees) and (0.10,10 degrees). The p=0.08 and p=0.30
settings use (0.10,10 degrees). Public evaluation has 100 trials per setting;
hidden evaluation has 200, 200, 150, and 100. Instances are shared by all methods
in an evaluation. Public and hidden random families are independent.

Each trial first fits one global right gauge. Quaternion double-cover signs
are treated consistently. Rotation error is
`2 acos(2 <q1,q2>^2 - 1)` (range 0 to 2 pi, the paper's convention).
Translation error is Euclidean distance after alignment. Each trial averages
all 100 nodes. Metrics are the untrimmed mean, population standard deviation,
90th percentile (linear interpolation), and maximum of those trial averages,
separately for rotation and translation. Lower is better for all eight.

The evaluator fixes the inputs, true poses, comparison solvers, reference,
and task thresholds. If either mean error in any setting reaches half that of
the fixed identity-pose estimate on the same instances, the attempt fails.
Invalid or failed attempts have no rank and sort below every successful one;
there is no compensating reward from other metrics. Measurable raw errors may
still be retained for diagnosis.

For successful attempts, rank is the sum over experiments and metrics of
`weight * abs(coefficient) * direction * (value-reference) / population_std`.
Direction is +1 for higher-is-better metrics and -1 otherwise. The scale is
computed across successful candidate attempts on disk and the frozen reference;
evaluator-owned baselines do not enter this population. An exactly constant
metric contributes zero. Adding attempts changes numerical rank scales, so
ranks from different cohorts are not numerically comparable. Failure always
precedes this arithmetic. `scoring/reference.json` defines coefficients, with
identical fixed evaluator snapshots.

The evaluator saves raw outputs in its own slice cache. `--reuse-outputs`
recomputes every metric from those poses, checking the exact input fingerprint;
it never imports a method's score or verdict. Default evaluation always runs
all discovered solvers. Hidden raw poses, inputs, and per-trial errors remain
inside eval/test/. Neither evaluation slice imports the other or method/.
