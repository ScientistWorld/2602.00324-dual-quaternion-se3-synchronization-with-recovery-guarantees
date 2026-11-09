# Final hardening

The hidden test now separates the honest stronger and weaker controls by much
more than seed variation, and every repaired shortcut fails without a rank.
One requested scientific condition remains unresolved: the reproduction does
**not** establish the paper's uniform superiority over matrix EIG. That
comparison is retained, rather than weakened or hidden. The supported scope is
synthetic pose recovery and improvement over the rounded DQ initializer.

The complete joint audit was job `00902d7f-40f`. It regenerated the reference,
all fixed baselines, seed controls, stronger/weaker methods, and repaired
shortcuts from final solver code. Its final assertion rejected the
matrix-comparison claim after saving all numerical results. Final packaging
uses those saved raw outputs; no solver changes or retraining are involved.
Aggregate evidence is in `redteam/hardening/report.json`. Hidden raw outputs,
inputs, and per-trial errors stay inside `eval/test/.cache/`.

## Does better science score higher?

The old ranks below are the REDTEAM all-finite-attempt cohort. The new ranks
use the final successful-attempt cohort and a frozen reference. Since each
metric is divided by its variation across that cohort, magnitudes across the
two columns are not directly comparable. Their ordering and paired intervals
are the relevant checks.

| Method | Before rank | After hidden rank | Paired 95% interval after |
|---|---:|---:|---:|
| Stored / final reference | 0 | 0 | fixed anchor |
| Reference seed 0, fresh | −0.081313 | 0 | same as anchor |
| Reference seed 1 | −0.033993 | +0.000077 | [−0.000051, +0.000121] |
| Reference seed 2 | −0.264303 | +0.000024 | [−0.000086, +0.000051] |
| Stronger noise-aware refinement | +0.496262 | **+8.488435** | **[+8.195607, +8.990637]** |
| Weaker rounded DQ spectral estimator | −0.122511 | **−1.342277** | **[−1.697141, −0.884850]** |
| One power iteration | −9.475122 | failed, unranked | failed recovery threshold |
| Matrix EIG, registered as an honest candidate | not run | +0.821314 | [−0.103495, +1.333172] |

The old weaker-versus-fresh-reference gap was only 0.041198, smaller than the
0.230310 range across reference seeds. After fixing the translation origin and
freezing the default initializer seed, the three-seed hidden rank range is
0.000076535. The stronger gain and weaker loss exceed that range by orders of
magnitude. Every method sees the same instances. Mean-error uncertainty uses
1,000 paired bootstrap resamples; complete weighted-rank uncertainty uses 500,
recomputing mean, standard deviation, p90, and maximum with common resampled
indices and the audit cohort's fixed metric scales.

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
over all metrics, with std taken across successful candidate attempts on disk
and the frozen reference. Direction comes only from `higher_is_better`.
Evaluator-owned baselines are comparisons, not extra reward terms. A failed
validity or recovery constraint makes the entire attempt failed and unranked,
so other metrics cannot compensate for failure.

## Major shortcuts

“Failed” below means status `failed` and rank `null`, below every successful
method. Every row was rerun through the hidden interface after the fixes.

| Shortcut | Before rank / behavior | Fix | After hidden result |
|---|---:|---|---|
| Rebuild answers from visible generator | +0.911938 | Test family and answer generator only in eval/test; solver receives measurements without seeds or truth | failed recovery |
| Enumerate the 100 public seeds | +0.911938, about 1.8 seconds | Independent private test family; exact public-bank fingerprint enumeration finds no hidden match | failed recovery |
| Replace truth / duplicate instance IDs | +0.911938 | Evaluator owns truth and IDs; strict duplicate-key rejection; only raw pose fields accepted | rejected |
| Return one pose with n=100 metadata | +0.911938 | Actual arrays must contain exactly the requested node count; submitted metadata ignored/rejected | rejected |
| Select easiest trials | +0.685948 | Exact full evaluator-owned ID set and test size | rejected |
| Substitute p=0.30 low-noise data | +0.911937 | Evaluator fixes graph, noise, instances and truth | failed recovery |
| Forge an oracle comparison baseline | +11.078712 | Fixed comparison implementations and operating points in eval; no submitted comparison accepted | rejected |
| Identity poses plus forged baseline compensation | +4.231233 | Complete-task validity/recovery gate precedes rank; candidate's own errors only | rejected |
| NaN translation | exit 0 with NaN metric; no valid finite old rank | Strict finite JSON and pose checks; impossible metrics fail | rejected |
| Negative/scalar score or success-flag forgery | New probe; old forged scalars already scored −6.928792 | Output schema accepts poses only; evaluator recomputes every number and verdict | rejected |

For additional evidence that the hidden instances are unseen, public-bank
lookup, answer reconstruction, and easier-input substitution all scored
+7.958661 on development in this audit, then failed hidden recovery. Genuine
methods did not suffer that distribution gap.

Existing empty/null and constant-output attacks were already nonwinning in
REDTEAM and were not replayed. Their defenses remain; small protocol checks
also reject nulls, booleans, overflow, NaN/infinity, nonunit rotations,
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
translation and has nominal rank +0.821314; its paired interval crosses zero.
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
