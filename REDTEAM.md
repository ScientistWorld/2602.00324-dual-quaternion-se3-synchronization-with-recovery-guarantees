# Scoring audit: SE(3) synchronization

**Partial pass for scientific sensitivity; fail as a ranking of scientific contribution.** A genuine noise-aware estimator scores higher than the reference by more than the three-seed spread, and a severely weakened solver scores much lower. Removing the projected refinement scores lower, but by less than the seed spread: the test does not reliably distinguish the key refinement from its initializer. The implementation beats its available DQ spectral baseline in both mean errors, but the paper's matrix-EIG comparison has not been reproduced because that baseline is absent.

The strongest scoring failure is a task-failing constant-output method that outranks the reference by changing another scored artifact. Several other shortcuts obtain essentially perfect recovery scores without recovering the requested poses.

The hidden script emits metric JSON, not a scalar rank. Scores below apply the requested ranking rule to the 17 finite attempts in this audit: sum over both scored method entries, experiments, and metrics. Higher scores are better; the stored reference is zero. The exact score of a future attempt depends on the other attempts later ranked. Raw metrics, cohort membership, and both all-entry and proposed-only calculations are in [redteam/summary.json](redteam/summary.json).

| Honest variant / control | Low-noise R / T | High-noise R / T | Test rank vs stored reference |
| --- | ---: | ---: | ---: |
| [Stored reference, rescored unchanged](redteam/reference_stored_artifacts/run.sh) | 0.107290 / 0.133748 | 0.181609 / 0.240346 | -0.000000 |
| [Original implementation, seed family 0](redteam/reference_seed0/run.sh) | 0.106247 / 0.141499 | 0.180734 / 0.247834 | -0.081313 |
| [Original implementation, seed family 1](redteam/reference_seed1/run.sh) | 0.107145 / 0.126112 | 0.181601 / 0.221621 | -0.033993 |
| [Original implementation, seed family 2](redteam/reference_seed2/run.sh) | 0.109383 / 0.142345 | 0.181850 / 0.243337 | -0.264303 |
| [Genuinely stronger: noise-aware refinement](redteam/better_noise_aware/run.sh) | 0.072942 / 0.056601 | 0.122595 / 0.098821 | +0.496262 |
| [Weaker: spectral initializer, no GPM](redteam/weaker_spectral/run.sh) | 0.110839 / 0.147845 | 0.190247 / 0.260935 | -0.122511 |
| [Clearly weaker: one initializer iteration, no GPM](redteam/weaker_one_iteration/run.sh) | 4.282051 / 2.633644 | 4.282494 / 2.634112 | -9.475122 |

All honest variants use 100 poses, the original noisy measurements, and 100 trials per setting. The stronger solver receives only noisy edges, an initial estimate, and the declared noise levels. It adds variance-weighted quaternion least squares and regularized translation estimation; it never receives truth. The weak variants remove refinement or also truncate initialization. The common DQ spectral comparison is held fixed across these runs.

The stronger method gains **0.577575** over the fresh seed-0 reference, exceeding the **0.230310** seed range. The one-iteration variant loses **9.393809**. Removing only refinement loses **0.041198**, below that range and therefore noise under the requested criterion. These conclusions persist when normalization uses only the seven honest/control attempts: stronger gain 0.535867, severe-weakening loss 10.149364, refinement-removal loss 0.040932, seed range 0.191333.

No scored reference metric is already at its bound: zero-bound entries are **none**, across all 32 values (eight metrics, two experiments, two method entries). Both rotation and translation means, standard deviations, p90s, and maxima are strictly positive. There is room above the reference: the genuine stronger method substantially lowers both mean errors. However, the available simple spectral baseline sits very close to the reference rather than clearly below it: R/T are 0.110839/0.147845 versus 0.106247/0.141499 at low noise, and 0.190247/0.260935 versus 0.180734/0.247834 at high noise. Its rank gap is smaller than seed noise.

**Three-seed spread and reproduction check.**

Seed families use `260200324 + i + 7919*j`, with `i=0,1,2` and `j=0,...,99`. Each run executes the unmodified `method.sync` implementation at n=100, initialization cap 2000/tolerance 1e-5 and GPM cap 200/tolerance 1e-8. The hidden slice contains 57, 56, and 57 trials respectively. This measures variation from regenerated instances and initializer randomness, not repeated timing noise. Each table entry below is max minus min across the three test runs.

| Scored metric | Low-noise spread | High-noise spread |
| --- | ---: | ---: |
| `error_R` | 0.003136 | 0.001116 |
| `error_R_std` | 0.004946 | 0.007752 |
| `error_R_p90` | 0.009905 | 0.015049 |
| `error_R_max` | 0.039648 | 0.059310 |
| `error_T` | 0.016233 | 0.026213 |
| `error_T_std` | 0.029392 | 0.038328 |
| `error_T_p90` | 0.012572 | 0.027287 |
| `error_T_max` | 0.229089 | 0.361141 |

The all-entry seed-score range is 0.230310; the proposed-only range is 0.230310. Treat smaller gains as noise. Three seeds estimate a spread, not a confidence interval.

The saved artifacts reproduce the stored test metrics to 8.8e-15 when rescored, but rerunning the current source with their seeds does **not** regenerate their poses: the largest test-metric discrepancy is 0.068982. Truth, seeds, and recorded settings agree. Fifty of 100 trials per setting differ; the differences concentrate on isolated nodes, with one trial also changing nodes 9 and 56. This is consistent with the documented change to zero-entry projection behavior, but does not establish the historical cause. The original and vectorized implementations agree across all 200 seed-0 trials to less than 4.0e-15 in pose components and 1.7e-14 in aligned errors. Final scientific comparisons use the unmodified implementation; the vectorized pilot is excluded. See [consistency evidence](redteam/reference_consistency.json) and [protocol diagnostics](redteam/protocol_diagnostics.json).

The available baseline is the rounded **dual-quaternion spectral initializer**, not the paper's matrix-EIG method. The direction of the internal comparison agrees with the paper's reported direction (lower mean rotation and translation errors), but it does not verify the paper's external-comparator claim. On all 100 original trials, DQGPM R/T means are 0.107204/0.144044 versus initializer 0.111462/0.149974 at low noise, and 0.180794/0.247865 versus 0.190213/0.260447 at high noise.

Departures from the paper's experimental reproduction are:

- The external matrix-EIG baseline is replaced by the DQ initializer. The external SDR/real-data comparisons and reported CPU-time comparison are absent from scoring; SDR was itself excluded from the paper's synthetic Table 2.
- Only two of Table 2's twelve noise/density combinations are scored. There are no scored real scan-registration experiments.
- The paper reports 100-trial results and 15% trimmed means. The gym uses untrimmed means on a deterministic seed-modulo subset (57 trials for the reference). Under an interpretation that trims 15% from each tail, the original 100-trial DQGPM R/T means are 0.101277/0.129230 and 0.175768/0.226741. They remain materially above the paper's 0.034/0.069 and 0.035/0.132, so trimming alone does not explain the gap.
- The implementation chooses numerical zero thresholds, a relative Euclidean residual over the stacked standard/dual coordinates, a 2000-iteration initializer cap, and a 200-iteration GPM cap with tolerance 1e-8. Section 4.2 specifies initializer residual below 1e-5 but does not specify this complete stopping policy. The code does contain the paper's shifted DQ measurement model, dual-norm power iteration, and projected matrix iteration; it is not an end-to-end surrogate.
- The public generator exposes truth and all trial seeds. The hidden test scores agent-supplied labels and predictions rather than independently generating held-out instances. The original 100-node problem size is retained.

**Shortcut runs.**

Every row has its own linked `run.sh`; the same directory retains `scores_train.json`, `scores_test.json` when emitted, and `result.json` with return codes. Each candidate is prepared in a Python process that exits before a separate `bash scripts/evaluate_test.sh` invocation with **no arguments**. No evaluator, evaluator process, or Python installation is modified. Candidate construction uses visible generator/method/train modules; hidden reference files are used only by audit controls and rank analysis. Working artifacts and original score files are restored after each case.

| Shortcut | What it does | Test rank vs reference = 0 | Result |
| --- | --- | ---: | --- |
| [shortcut_rebuild_answers](redteam/shortcut_rebuild_answers/run.sh) | Use the public generator and public seeds to copy `.truth` to predictions. | +0.911938 | Works: R mean ≈1.08e-9, T=0 in both settings. |
| [shortcut_rewrite_truth](redteam/shortcut_rewrite_truth/run.sh) | Write constant truth and predictions in a duplicate `outputs/z_...` artifact; last duplicate wins. | +0.911938 | Works: all 16 proposed metrics are exactly zero. |
| [shortcut_bruteforce_seed_bank](redteam/shortcut_bruteforce_seed_bank/run.sh) | Enumerate all 100 public seeds per setting; identify an instance by three noisy non-diagonal edge records and return its stored truth. | +0.911938 | Works: 100/100 lookups per setting; same near-zero errors as answer reconstruction. |
| [shortcut_one_pose](redteam/shortcut_one_pose/run.sh) | Keep n=100 in metadata but supply only one truth pose and one identity prediction; gauge alignment fits it. | +0.911938 | Works: R=0, T≈3.26e-16, without recovering the 100 poses. |
| [shortcut_select_trials](redteam/shortcut_select_trials/run.sh) | Retain the easiest trial on each side of the visible modulo split, using visible error code. | +0.685948 | Works: one test trial; R/T=0.059019/0.051522 and 0.118790/0.103244; all standard deviations zero. |
| [shortcut_easier_inputs](redteam/shortcut_easier_inputs/run.sh) | Run the unchanged solver on p=0.30, zero-noise measurements while keeping scored experiment labels. | +0.911937 | Works: all proposed metrics below 8e-9. |
| [shortcut_replace_baseline](redteam/shortcut_replace_baseline/run.sh) | Keep the proposed method unchanged but replace the scored DQ spectral artifact with oracle estimates. | +11.078712 | Works: proposed outputs tie the fresh reference exactly; the scored comparator produces the gain. This tie is a shortcut. |
| [shortcut_compensate_failure](redteam/shortcut_compensate_failure/run.sh) | Return identity poses on every original node, while replacing the scored baseline with oracle estimates. | +4.231233 | Works under the requested all-entry sum: despite R=4.177225 and T=1.578763 in both tasks, it outranks the reference. |
| [shortcut_forged_scalars](redteam/shortcut_forged_scalars/run.sh) | Write -1e200 errors/timings, success flags, and a fabricated `scoring/scores_test.json`, with constant predictions. | -6.928792 | Fails: test recomputes errors and overwrites the score file; exactly the constant-output score. |
| [shortcut_constant](redteam/shortcut_constant/run.sh) | Return identity rotation and zero translation for every original pose, with original truth. | -6.928792 | Fails: R=4.177225, T=1.578763; correctly scores below reference. |
| [shortcut_empty](redteam/shortcut_empty/run.sh) | Supply empty truth and prediction arrays. | No finite score | Fails: exit 1, division by zero; no test score. |
| [shortcut_null](redteam/shortcut_null/run.sh) | Put a JSON null in a quaternion component. | No finite score | Fails: exit 1, float conversion error; no test score. |
| [shortcut_nan](redteam/shortcut_nan/run.sh) | Return NaN quaternion components. | No finite score | Fails to demonstrate a finite winning score: exit 0 emits R metrics=0 and T metrics=NaN. Invalid-score acceptance is a separate defect; downstream rank treatment is unproven. |

The brute-force shortcut builds and matches the complete public candidate family in 1.75 seconds and 1.81 seconds per setting, without solving synchronization. The entire shortcut case, including train/test evaluation, takes 7.01 seconds. **The effective test family is small and enumerable.** This does not mean that enumerating the continuous SE(3)^100 search space is feasible; it means the fixed public answer family makes that unnecessary.

Baseline replacement is an independent ranking failure. Under the stated rule that sums every scored entry, it gains +11.078712 with no change to the proposed solver. Combining it with a failed constant solver still scores +4.231233, so failure at the requested task can be compensated through other metrics. If a deployment instead ranks only `type=proposed` entries, those two diagnostic scores become -0.039168 (an exact tie with the fresh reference, and below the stored reference) and -6.886647 respectively. That narrower rule would remove the baseline-compensation gain, while answer reconstruction, truth replacement, undercoverage, trial selection, and easier inputs still win on the proposed metrics themselves.

The five near-perfect-output shortcuts and trial selection improve every proposed scored metric against the stored reference, independent of coefficient units or a particular positive normalizer. The scalar sizes shown here, including compensation across entries, are specific to the disclosed audit cohort. The seed-bank and generator shortcuts share a cause; they are separate demonstrated implementations, not claims of independent vulnerabilities.

**Ranking calculation and implications.**

The calculation is `sum_e,m,k weight[e] * abs(coefficient[e,k]) * direction[k] * (attempt[e,m,k] - reference[e,m,k]) / std_across_attempts[e,m,k]`. All eight directions are lower-is-better, so `direction=-1`. Experiment weights are 0.5 each; coefficient magnitudes are 1 for means, 0.25 for standard deviations, 0.35 for p90, and 0.2 for maxima. Negative coefficient signs do not reverse a metric. Each standard deviation is recomputed across the explicitly listed finite attempts (population standard deviation); invariant dimensions are omitted. This respects normalization by variation rather than using raw metric units. The stored test scores, not the paper's aspirational numbers, anchor zero.

The stability/tail metrics catch ordinary gross failure, but they are soft terms in a sum, not validity constraints. They neither enforce 100 nodes/100 prescribed trials nor bind labels, graph density, noise, or fixed comparators to the evaluator. Thus a method can win while omitting the task altogether.

The next gym iteration should generate evaluator-owned instances and truth after submission, use a solver interface that accepts only measurements, require exactly the prescribed nodes and trials, reject duplicate entries and non-finite/non-unit outputs, freeze comparisons, and exclude agent-writable baseline artifacts from rank. Keep baseline/constraint checks separately enforced rather than allowing them to compensate for failed recovery. Refresh the reference artifacts from the shipped source, strengthen the internal baseline separation, and either implement matrix-EIG or limit the claimed reproduction to the initializer comparison.

**Run record and workspace.**

Three CPU jobs completed successfully: `936aaff8-dd6` (vectorized pilot, 180 seconds), `22252f42-73f` (original reference and complete audit, 546 seconds), and `1d49ff41-09a` (final forgery/protocol diagnostics, 21 seconds). No GPU was required. The final batch has 20 cases: seven scientific/reference controls and thirteen shortcut probes. Re-run on a compute node with `bash redteam/run_all.sh`; `bash redteam/run_final.sh` adds the paper-protocol diagnostics. Large regenerated artifacts and logs are ignored under `redteam/.cache/`; small scores and diagnostics are committed.

All audited method, data, evaluator, environment, scoring, and original runner files are restored to their initial git contents. Pre-existing README/manifest device files and trajectory deletions are preserved. The required final `action.yaml` is the sole protocol exception to changes being confined to `redteam/` and this report. No reproduction milestone is upgraded by this audit.
