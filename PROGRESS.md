# Progress

## What Works

The workspace now contains a canonical implementation of the paper's synthetic
dual-quaternion synchronization pipeline: shifted ER measurement generation,
spectral power initialization, DQGPM refinement, and artifact-based scoring.

`eval/` no longer imports `method/`; it reads pose artifacts and computes
gauge-aligned rotation and translation errors independently.

The spectral initializer now uses the standard and dual parts of the
dual-quaternion vector norm, matching Algorithm 1 more closely than the
previous standard-part-only normalization.

Continuation audit on 2026-05-20 confirmed that `method/` implements the
paper's actual computational steps rather than a surrogate, `eval/` remains
artifact-based and independent from `method/`, and
`python3 validate.py --compare --post-reproducer` passes for the existing
scores.

Continuation validation job `b6338986-caa` reran the retained sparse suite
inside the compute container and passed `validate.py --compare
--post-reproducer` with the regenerated artifacts.

The latest audit found that the compute entrypoint depended on gitignored
checkpoint artifacts. `scripts/run.sh` now calls the full reproduction first,
so a fresh job rebuilds the core artifacts before scoring. It then probes
`p008_noise010`, `p030_noise005`, and `p030_noise010` into
`tmp/extension_scores.json` for possible expansion without overwriting the
accepted core `scores.json`.

The UDQ projection now implements the exact zero-entry fallback from
Proposition 2.7: zero components of a nonzero vector use a normalized nonzero
component instead of silently becoming identity. This rarely affects the
current diagonal synthetic matrix, but it closes an algorithmic mismatch.

Verifier audit on 2026-05-20 corrected the `p005_noise005` Table 2 reference
value for DQGPM translation error from `0.135 ± 0.043` to `0.069 ± 0.043`.
The main evaluator now emits the p90 and max stability metrics already
declared in `reference.json`, and `scripts/reproduce.sh` evaluates only the
two claimed sparse artifacts instead of globbing stale checkpoint files.

## Results

The first CPU smoke job completed with valid measured scores for five trials on
`p005_noise005`:

- `dqgpm`: `error_R=0.123`, `error_T=0.122`
- `dq_spectral`: `error_R=0.126`, `error_T=0.126`

This restores `method_runs`: the paper's algorithm executes end-to-end and the
independent evaluator scores its outputs. The gap was too small and the trial
count too low to claim `core_claim`, so the next job expanded to 30 trials over
all three declared Table 2 settings.

The 30-trial run completed successfully and showed DQGPM improving over the
rounded dual-quaternion spectral initializer in all three settings, but the
dense rotation error is still far above the near-zero paper number. I checked
the paper's data-generation specification against the implementation; the next
run uses 100 trials and corrected artifact labels to get paper-scale averages
before deciding the final milestone.

The 100-trial, 50-iteration run completed and validated. DQGPM improved over
`dq_spectral` in every scored setting:

- `p005_noise005`: translation error `0.135` vs `0.140`
- `p005_noise010`: translation error `0.239` vs `0.252`
- `p030_noise010`: translation error `0.074` vs `0.075`

Sparse-setting histories were capped by `max_iter=50` in nearly every trial.
The follow-up 100-trial run increased the GPM budget to 200 iterations while
keeping the same evaluation protocol. It completed successfully and produced
nearly identical scores, indicating that the sparse runs had effectively
settled at the fixed point reached by the implementation.

Final 100-trial, 200-iteration scores before the reference correction and
p90/max metric refresh:

| Experiment | Method | error_R | error_T | error_T_std |
| --- | --- | ---: | ---: | ---: |
| `p005_noise005` | `dqgpm` | 0.110003 | 0.134546 | 0.071228 |
| `p005_noise005` | `dq_spectral` | 0.114100 | 0.140277 | 0.071946 |
| `p005_noise010` | `dqgpm` | 0.183282 | 0.239062 | 0.112500 |
| `p005_noise010` | `dq_spectral` | 0.192591 | 0.251540 | 0.115673 |

These results support a narrow `core_claim`: the paper's DQGPM algorithm
improves the rounded DQ spectral initializer on both rotation and translation
error under the same generated graph/noise protocol for the two sparse
settings retained in `scores.json`. The corrected paper reference makes clear
that the absolute translation error for `p005_noise005` is still materially
worse than Table 2.

The continuation validation job `b6338986-caa` reproduced the same final
100-trial, 200-iteration scores and confirmed that the reusable scripts remain
container-runnable:

| Experiment | DQGPM error_T | DQ spectral error_T | DQGPM error_R | DQ spectral error_R |
| --- | ---: | ---: | ---: | ---: |
| `p005_noise005` | 0.134546 | 0.140277 | 0.110003 | 0.114100 |
| `p005_noise010` | 0.239062 | 0.251540 | 0.183282 | 0.192591 |

The follow-up CPU job `a5472b1a-918` expanded the scored suite with
`p008_noise010`, the Table 2 setting with `p=0.08`, `sigma_t=0.10`, and
`sigma_r=10 deg`. The job completed method and baseline runs, and DQGPM again
improved over the rounded dual-quaternion spectral initializer
(`error_T=0.152492` vs `0.159884`). However, post-reproducer validation failed
because the reproduced DQGPM translation error was 2.38x the paper's `0.064`.
That setting is therefore documented as attempted but excluded from the current
claimed scored suite.

## Remaining

Higher milestones would require broader reproduction work: implement the
paper's external matrix-EIG and SDR baselines, diagnose the mismatch on the
less sparse `p008_noise010` setting, add more Table 2 noise/density settings,
and diagnose why the dense `p030_noise010` run had `error_T=0.074253` versus
the paper's `0.027`.

## Issues

The inherited workspace had fabricated `scores.json` values and a
`reference.json` that did not match Table 2. The reference file has been
rewritten with actual paper values, and `scores.json` now contains fresh
measured results from the final job.

The evaluator previously emitted `n_trials`, which was not a declared metric in
`reference.json`; this has been removed so structural comparison is meaningful.

The artifact label `eig` was inaccurate: the implemented baseline is the
paper's rounded dual-quaternion spectral initializer, not the external
matrix-EIG baseline reported in Table 2. It is now labeled `dq_spectral`.

The final scores are worse than the paper's absolute DQGPM values. The
implementation still follows the paper's computation and improves over its
initializer, so the environment is usable at `core_claim`, but the Table 2 gap
should be treated as an open reproduction issue rather than a solved result.

The continuation review removed a misleading `eig` runner alias. The paper's
external matrix-EIG baseline remains only as a reported reference value until a
separate implementation is added.

Continuation audit on 2026-05-20 reset the active milestone to `method_runs`
pending a fresh compute-node validation. Lightweight checks passed for shell
syntax and Python compilation, and the next CPU job reruns the retained
100-trial sparse synthetic suite plus `validate.py --compare --post-reproducer`.

Validation rejected the dense `p030_noise010` result because its primary
translation metric was 2.75x the paper value. I re-read Table 2 and confirmed
the reference transcription is correct, so that setting is excluded from the
current scored target list instead of being claimed as reproduced.

Validation also rejected the attempted `p008_noise010` extension from job
`a5472b1a-918`: DQGPM still improved over the implemented initializer, but its
primary translation metric was too far from the paper's reported value. The
core sparse settings remain valid and are the only experiments in the final
`scores.json`.

The continuation validation job `b6338986-caa` produced no new errors. It
confirms the retained core suite remains reproducible after the audit cleanup
that removed the misleading `eig` runner alias and hardened
`scripts/evaluate.sh` against empty artifact globs.

The next submitted CPU job regenerates the validated core suite from scratch
after the projection and artifact-size fixes, then evaluates the three
extension settings separately. A higher milestone should only be claimed if
those extension results support the paper's trend and pass the same
paper-consistency checks after being promoted into `reference.json`,
`TARGETS.md`, and `scores.json`.

## Deviations from Paper

The completed smoke job used 5 trials and the next job used 30 trials rather
than the paper's 100 trials to test the container and pipeline quickly. The
final reported scores use 100 trials per scored synthetic setting. This
reproduction implements the paper's DQGPM method and rounded DQ spectral
initializer, but not the external matrix-EIG or SDR comparison methods.

The DQGPM iteration cap is 200 for the final run. The paper stops by residual
tolerance and does not emphasize a fixed cap; this cap is a compute budget
guard, and the 50-iteration and 200-iteration runs gave the same measured
scores to the displayed precision.

Diagnostic DQGPM histories are no longer stored by default. The method still
uses the same iterates, but artifacts now keep only final estimates unless
`--record-history` is requested for plotting or convergence analysis.

## 2026-11-09: final hardening, joint verification pending

Read the paper and REDTEAM.md. Finished the incomplete measurement-only
transition; fixed evaluator ownership, strict validation and failure gating,
variance-normalized ranking, independent private test generation, matrix-EIG
rounding, and runnable scripts. Expanded the original n=100 study to four paper
settings. All changes precede one joint compute job, including reference,
seed controls, stronger/weaker methods, fixed comparisons, and repaired attacks.
No heavy computation was run on the login node. Static compilation and
`python3 validate.py` pass; numerical claims await the job.

### Environment portability correction

The scheduler rejected the GHCR base before building or submitting the joint
check. Switched to Docker Hub python:3.11-slim-bookworm. The scheduler setup
wrapper supplies uv from its host mount, so package installation remains in
setup.sh and container.def contains only OS package installation. No numerical
experiment has run; the same joint verification is being resubmitted.

### Setup path correction

The second submission built its container but failed setup: the host-mounted
workspace is not /home/user during dependency installation. Setup now resolves
the local wheel relative to BASH_SOURCE and falls back to the pinned public
package during the internet-enabled setup phase when a fresh clone has no
wheel. Runtime compute remains offline. No scientific job has run yet.

### Joint check 817ad207-04c: incomplete, corrected and resubmitted

The container built and the protocol and arithmetic checks passed. Reference
and fixed comparisons ran from final code, but temporary solver input files
filled the container's /tmp before the control suite completed. Their resulting
I/O failures are not evidence of closed shortcuts. The audit analysis failed
and was incorrectly allowed to continue packaging; that path now fails the job.
Solver files now live under each evaluator's cache and are removed after each
experiment, keeping hidden inputs within eval/test/.

Completed comparisons also exposed a free translation-origin mismatch: power
initialization leaves an arbitrary noncompact gauge while the matrix baseline
chooses a centered origin. All reference and baseline outputs now use the same
zero-mean body-translation representation, preserving every relative pose and
the paper's algorithm. A joint rerun will include relative-pose invariance,
reference and all baselines, seed controls, stronger/weaker methods, and every
repaired attack. Matrix-baseline rank and paired confidence bounds are also
checked explicitly. No new numerical success is claimed from the incomplete
job; milestone stays core_claim pending verification.

### Joint audit 00902d7f-40f: numerical checks completed; external comparison unresolved

The complete final-code audit ran every solver and repaired attack on all four
settings. Stronger hidden rank is +8.488435 (paired 95% interval
[8.195607,8.990637]); weaker spectral rank is -1.342277
([-1.697141,-0.884850]); three-seed reference rank range is 0.000076535.
All repaired shortcuts failed and are unranked. Reference mean errors on train
and test agree closely. The algorithm and protocol checks passed.

The job's final assertion correctly exposed that uniform superiority over
matrix EIG is not reproduced: EIG's candidate rank is +0.821314 with interval
[-0.103495,1.333172]. A source audit found no justified corrective change;
weights and the comparator are retained. The report now records this as an
unresolved requirement and limits the claimed reproduction to synthetic
recovery/refinement. Core scientific ordering and attack assertions stay fatal.

Prepared final packaging from saved raw outputs only: regenerate canonical
reference-only train/test scores, freeze measured gym-scale targets without
changing paper numbers, assert artifact consistency, and run all validator
modes. No method/evaluator changes require another inference run. After this
job, scripts/run.sh will return to end-to-end reproduction.
