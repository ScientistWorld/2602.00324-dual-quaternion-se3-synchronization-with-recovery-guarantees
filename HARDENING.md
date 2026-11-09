# Final hardening

The hidden test separates the honest stronger and weaker controls by much
more than seed variation. Every repaired shortcut scores below every successful
attempt, with finite worst-case values in all 32 scored fields. Rejected and
missing manifests are failed candidates, and ranking normalizes over all
candidate attempts on disk. The final joint check passed.
One requested scientific condition remains unresolved: the reproduction does
**not** establish the paper's uniform superiority over matrix EIG. That
comparison is retained, rather than weakened or hidden. The supported scope is
synthetic pose recovery and improvement over the rounded DQ initializer.

The complete inference audit was job `00902d7f-40f`. It regenerated the reference,
all fixed baselines, seed controls, stronger/weaker methods, and repaired
shortcuts from final solver code. Its final assertion rejected the
matrix-comparison claim after saving all numerical results. The final
evaluator-only fixes were applied together and checked in job `79663ce3-a6a`
(exit 0, 120 seconds), using those saved raw outputs. No solver, comparator,
or data change required new inference. This job rescored the reference,
baselines, seed controls, stronger/weaker controls and repaired shortcuts on
both slices, checked paired uncertainty and the failure protocol, regenerated
canonical reference/baseline scores, and passed package validation.
The validator emits three heuristic warnings about random-number generation
in the test-input generator and frozen comparison solvers. Submitted methods
are scored from their raw poses; the hidden interface runs inference and
performs no training. Artifact-consistency and protocol checks passed.
`redteam/hardening/packaging_check.json` explicitly records
`all_requested_conditions_met: false` for the unresolved EIG comparison.
`scripts/run.sh` is restored to end-to-end reference reproduction.
Aggregate evidence is in `redteam/hardening/report.json`. Hidden raw outputs,
inputs, and per-trial errors stay inside `eval/test/.cache/`.

## Does better science score higher?

The old ranks below are the REDTEAM all-finite-attempt cohort. The new ranks
use all final candidate attempts, including failures, and a frozen reference. Since each
metric is divided by its variation across that cohort, magnitudes across the
two columns are not directly comparable. Their ordering and paired intervals
are the relevant checks.

| Method | Before rank | After hidden rank | Paired 95% interval after |
|---|---:|---:|---:|
| Stored / final reference | 0 | 0 | fixed anchor |
| Reference seed 0, fresh | −0.081313 | 0 | same as anchor |
| Reference seed 1 | −0.033993 | +0.0000003154 | [−0.0000001155, +0.0000005167] |
| Reference seed 2 | −0.264303 | +0.0000001082 | [−0.0000003279, +0.0000003198] |
| Stronger noise-aware refinement | +0.496262 | **+0.156129** | **[+0.154125, +0.159224]** |
| Weaker rounded DQ spectral estimator | −0.122511 | **−0.025081** | **[−0.026678, −0.022918]** |
| One power iteration | −9.475122 | −7.364029, failed | failed recovery threshold |
| Matrix EIG, registered as an honest candidate | not run | +0.008799 | [+0.004819, +0.011829] |

The old weaker-versus-fresh-reference gap was only 0.041198, smaller than the
0.230310 range across reference seeds. After fixing the translation origin and
freezing the default initializer seed, the three-seed hidden rank range is
0.0000003154. The stronger gain and weaker loss exceed that range by orders of
magnitude. Every method sees the same instances. Mean-error uncertainty uses
1,000 paired bootstrap resamples; complete weighted-rank uncertainty uses 500,
recomputing mean, standard deviation, p90, and maximum with common resampled
indices and the audit cohort's fixed metric scales.

Immediately before this final evaluator patch, the same raw-output cohort
gave stronger/weaker ranks +8.488435/−1.342277 and failed attempts null ranks
with empty or partial metric entries. Those magnitudes used only successful
candidates for normalization. The final all-attempt normalization changes the
units of rank; it preserves the strong ordering and now makes every failed
attempt costly to consumers of the numeric metrics as well as status flags.
Reference rank remains exactly zero before and after. Re-aligning its saved
poses changed no scientific metric by more than 2.8e-17.

The reference and honest controls also behave alike on development and test.
For example, reference development R/T means are 0.107338/0.077709 and
0.180722/0.135395 on the two sparse settings, versus hidden
0.108040/0.077601 and 0.179398/0.134035. Public-answer memorization still wins
on public instances and fails on the private instances; this is the intended
generalization distinction.

## Reference recovery and headroom

| Hidden setting | Reference R/T before | Reference R/T after | DQ spectral R/T after | Stronger R/T after |
|---|---|---|---|---|
| p005_noise005 | 0.107290 / 0.133748 | 0.108040 / 0.077601 | 0.113220 / 0.081901 | 0.075657 / 0.055027 |
| p005_noise010 | 0.181609 / 0.240346 | 0.179398 / 0.134035 | 0.189593 / 0.142989 | 0.121707 / 0.096609 |
| p008_noise010 | absent | 0.112537 / 0.086686 | 0.117958 / 0.090836 | 0.050204 / 0.058766 |
| p030_noise010 | absent | 0.052201 / 0.040496 | 0.052587 / 0.040897 | 0.015738 / 0.026606 |

No reference metric sits at its lower bound: all 32 scored statistics are
strictly above zero, and all vary across the honest methods. No tried variant
reaches all bounds. The stronger method improves both means in every setting,
retaining substantial error even on the denser experiment. Its gain supplies
headroom independently of the competitive matrix baseline.

The added p=0.08 and p=0.30 experiments extend the paper's own noise/density
study at its original n=100. They expose the remaining noise floor when sparse
graph ambiguity is reduced. The old test selected 57 public-seed trials; the
new hidden sizes are 200/200/150/100, with 100 development trials per setting.
Sparse settings retain 60% total weight; added settings receive 25% and 15%.
This weights noise handling as well as sparse recovery. Per-metric coefficient
magnitudes remain 1 for each mean, 0.25 for standard deviation, 0.35 for p90,
and 0.20 for maximum. No weights were adjusted in response to the EIG result.

Rank adds `weight * abs(coefficient) * direction * (value-reference) / std`
over all metrics, with std taken across all candidate attempts on disk
and the frozen reference. Direction comes only from `higher_is_better`.
Evaluator-owned baselines are comparisons, not extra reward terms. A failed
validity or recovery constraint assigns evaluator-owned worst-case values to
the entire attempt, so other metrics cannot compensate for failure. For N
nonnegative trial errors with passing mean below L, maximum is below N*L,
standard deviation below sqrt(N-1)*L, and the interpolated p90 is bounded by
N*L/(N-ceil(0.9*(N-1))). Rotation also has its physical bounds. Each penalty
exceeds the corresponding passing bound by 1% plus 1e-9. This guarantees every
failure scores below every successful attempt in every field, even for a
consumer that ignores status metadata. Missing, malformed, reserved, and
duplicate manifests receive the same complete penalties. Rejected manifests
use a reserved evaluator namespace, so their entries cannot be overwritten.
The penalties are failure sentinels; actual errors remain separate diagnostics.

## Major shortcuts

“Failed” below means status `failed`, rank −7.364029 in the final audit cohort,
and worst-case penalties in every metric of every experiment. Every row's raw
output was rescored through the hidden interface after the evaluator fixes.

| Shortcut | Before rank / behavior | Fix | After hidden result |
|---|---:|---|---|
| Rebuild answers from visible generator | +0.911938 | Test family and answer generator only in eval/test; solver receives measurements without seeds or truth | −7.364029, failed recovery |
| Enumerate the 100 public seeds | +0.911938, about 1.8 seconds | Independent private test family; exact public-bank fingerprint enumeration finds no hidden match | −7.364029, failed recovery |
| Replace truth / duplicate instance IDs | +0.911938 | Evaluator owns truth and IDs; strict duplicate-key rejection; only raw pose fields accepted | −7.364029, rejected |
| Return one pose with n=100 metadata | +0.911938 | Actual arrays must contain exactly the requested node count; submitted metadata ignored/rejected | −7.364029, rejected |
| Select easiest trials | +0.685948 | Exact full evaluator-owned ID set and test size | −7.364029, rejected |
| Substitute p=0.30 low-noise data | +0.911937 | Evaluator fixes graph, noise, instances and truth | −7.364029, failed recovery |
| Forge an oracle comparison baseline | +11.078712 | Fixed comparison implementations and operating points in eval; no submitted comparison accepted | −7.364029, rejected |
| Identity poses plus forged baseline compensation | +4.231233 | Complete-task validity/recovery gate precedes rank; candidate's own errors only | −7.364029, rejected |
| NaN translation | exit 0 with NaN metric; no valid finite old rank | Strict finite JSON and pose checks; impossible metrics fail | −7.364029, rejected |
| Negative/scalar score or success-flag forgery | New probe; old forged scalars already scored −6.928792 | Output schema accepts poses only; evaluator recomputes every number and verdict | −7.364029, rejected |

For additional evidence that the hidden instances are unseen, public-bank
lookup, answer reconstruction, and easier-input substitution all scored
+0.465918 on development in this audit, then failed hidden recovery. Genuine
methods did not suffer that distribution gap.

The full historical constant-output and empty/null solver runs were not
replayed. Protocol fixtures now explicitly exercise missing, malformed,
reserved and duplicate manifests, empty/partial IDs, invalid JSON and recovery
failure through each scorer's main entrypoint. Every failure receives all
metric keys and ranks below the valid control. Smaller checks also reject
nulls, booleans, overflow, NaN/infinity, nonunit rotations,
nonorthogonal dual parts, huge translations, partial IDs, and forged truth or
baselines. The same checks verify coefficient-sign invariance, unit invariance,
metric direction, and failure precedence on both independent evaluators.

## Implementation and packaging fixes

The actual Algorithms 1 and 2 are retained: dual-number vector normalization,
unprojected spectral initialization, Hermitian dual-quaternion multiplication,
and entrywise UDQ projection. Vectorized multiplication was checked against
the original per-entry computation to within 1.8e-15. The initializer's
arbitrary translation origin was removed at serialization by one common right
translation that makes mean body-frame translation zero. This preserves every
relative pose and every algorithm iterate; its invariance was explicitly
checked. All reference and baseline serializers use the same convention. It
removes seed-dependent translation inflation under the paper's alignment.

The matrix comparator now uses homogeneous-row nullspace/least-squares
rounding, as described in the [EIG source paper, section 2.2](https://fusiello.github.io/papers/siims16.pdf).
Disconnected components are solved separately, with identity at isolated
nodes, using no truth. The shared output origin is an explicitly documented
convention. The matrix implementation was not degraded to force an ordering.

Alignment now removes the mean body-frame translation in the evaluator too,
before fitting the paper's gauge. A method's arbitrary global origin then
cannot alter scientific error under imperfect recovered rotations. The
reference already serialized this convention; its algorithm is unchanged.
Both independent evaluators are checked with a common right translation and
rotation applied to deliberately imperfect estimates.

Evaluation recomputes all scored statistics from raw complete poses; every
baseline, reference, threshold, setting and comparison implementation is
owned by eval. Train and test share no code or imports, and eval never imports
method. Test answers and their generator exist only in eval/test. The hidden
test performs inference, never training. No-argument evaluate_test.sh discovers
all registered solver manifests, without hardcoding a submitted method name.

The first joint job (817ad207-04c) filled /tmp and incorrectly continued after
an incomplete audit. That was not a successful verification. Temporary solver
inputs now stay in the appropriate evaluator cache, are deleted after each
experiment, and evaluator I/O failures stop the job. Scientific and shortcut
checks remain fatal; the unresolved external comparison is separately exposed
in the report as `all_requested_conditions_met: false`.

The container now uses Docker Hub python:3.11-slim-bookworm and only OS package
installation in container.def. setup.sh resolves its wheel relative to its
own location and can install the pinned dependency during internet-enabled
setup. download.sh includes the real public wheel fetch and checksum. Runtime
needs no internet, external model, dataset, or shared directory.

The paper's reported Table 2 values remain unchanged under `_paper_reported`
in scoring/reference.json. Its 15% trimmed statistics are historical context,
not targets for the gym's untrimmed statistics and added tail metrics. Numeric
gym targets and canonical train/test score files come only from final-code
reference runs and fixed baselines; audit-only candidate scores stay in the
audit report. No seed or setup was selected to match a paper value.

## Remaining limitations and shortcuts left

The published **uniform advantage over matrix EIG is unreproduced**. Hidden
EIG R/T means are 0.112000/0.071695, 0.181953/0.128651,
0.112205/0.085952, and 0.051901/0.040949. It trades rotation against
translation and has rank +0.008799 with paired interval [+0.004819,+0.011829].
Under the required all-attempt normalization it is measurably above the
reference, strengthening rather than resolving this negative finding.
Copying that honest estimator is an allowed alternative, not a loophole or the
headroom evidence. The weaker DQ spectral baseline is clearly below the
reference, while the stronger control is clearly above both. The reproduction
has the paper's procedure and original node count; no justified remaining
setup correction was identified that establishes the EIG claim. This requested
condition is left unmet, and no full-paper success is claimed.

General optimization on the supplied observations remains allowed. For this
continuous estimation problem, more optimization can be a scientific method;
it does not compute hidden truth. Exhaustive lookup of the finite public
instance bank no longer solves the hidden test. Direct hidden-file access,
code tampering, and malicious external side effects remain for the separate
attempt grader; no defenses target leftover processes or Python environments
in the fresh test container.

The test is finite, so max/p90 estimates retain sampling uncertainty and the
reported bootstrap intervals are conditional on this cohort's metric scales.
The package does not establish theoretical recovery guarantees or reproduce
SDR, real scan registration, or runtime-speed claims. These are not scored
experiments. Historical modulo-split and paper-matching claims in old logs are
superseded by the final protocol.
