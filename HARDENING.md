# Hardening (final iteration)

This iteration addressed REVIEW.md: it adds the paper's real-data experiment
(Sec. 4.3, Table 4: multi-view registration of Stanford 3D Scanning Repository
scans, ICP relative motions, the paper's (1 mm, 1 deg) perturbation, reference,
EIG and SDR run on it). It also brings the synthetic setup to a well-posed
version of the paper's settings and states plainly where the paper's
comparisons do not reproduce. Along the way it fixed one evaluator flaw that
made a better method score lower, closed three new shortcuts, and replayed the
previously repaired ones.

**Bottom line.** Better results now score higher: the stronger control ranks
+0.0960 on the hidden test (paired 95% interval [+0.0949, +0.0970]) and the
weaker control −0.0190 ([−0.0198, −0.0183]). Seed variation is 4.6e‑9 in rank.
Every shortcut probe fails or ties the reference exactly. Matrix EIG ties the
reference (+0.0003), and SDR is slightly more accurate on the scan experiments
(+0.0005). The paper's claimed superiority of DQGPM over EIG, and the
EIG/SDR failures it reports on sparse scan graphs, do **not** reproduce.

Jobs: `1937b8a9-ec3`, `6be339e4-0cc` and `f93ae350-634` were failed builds
(wrong `.conf` convention; identity-start ICP too weak; inconsistent quaternion
signs). They are described below because each exposed something real.
`8544621f-ca5` ran the full cohort. `5b98f5bd-c2d` (exit 0) rescored every saved
raw output after the evaluator alignment fix and passed
`validate.py --compare --post-design` and `--post-reproducer`. The evidence is
in `redteam/hardening2/` (`report.json`, `diag_before.json`,
`scores_{train,test}_all.json`).

## What changed

1. **Real-scan experiments `scan_sparse` and `scan_dense` (new, scored).**
   - `eval/test/build_scans.py` registers every pair of scans with
     point-to-point ICP (Besl & McKay). Scan sets: bunny (10 scans), Buddha
     standing (15), dragon standing (15), Armadillo standing (12).
     - *Dense* graphs start ICP from the turntable angle in the file names.
     - *Sparse* graphs use no pose prior: multi-start ICP from 121 fixed
       rotations, keeping the best fit by overlap. Identity-only starts
       registered just 4 of 45 bunny pairs.
   - A pair is observed when ICP converged to the repository alignment
     (≥5% overlap at 1 mm, within 3° and 5 mm). Pairs with the largest
     overlap are kept, up to the paper's Table 4 edge counts.
   - Ground truth is the repository's `.conf` alignment. That file maps scan
     points by `R(q)^T p + t`; the builder detects this from the data, with a
     0.64 vs 0.008 overlap separation.
   - ICP error relative to the repository alignment averages 0.24–1.07° and
     0.38–1.23 mm per kept edge, depending on the configuration. Hidden edge
     counts are 12/27/30/24 (sparse; paper 21/30/37/24) and 51/62/42 (dense;
     paper 90/84/52).
   - The graphs (`eval/test/scans.json`) and the raw scans (`eval/test/.raw`,
     fetched by `download.sh`) live only in `eval/test/`. The public train
     slice uses other scan sets of the same repository: Buddha and dragon on
     their side, back and upright (`eval/train/scans.json`).
   - **Per trial.** Every hidden trial (100 per configuration) re-expresses
     each scan in a fresh random rigid frame, randomly relabels the scans, and
     right-multiplies each relative pose by the paper's perturbation (angle
     N(0, 1°) about a uniform axis, translation N(0, 1 mm) per axis). This keeps
     the noise distribution and graph exactly as specified.
   - **Sign lift.** Measurement signs are lifted consistently with the truth
     representatives, as the paper's model `C = x x^* + Δ` assumes. Without
     the lift, 10–20% of edges carried the opposite sign. DQGPM then failed the
     task (train dense rotation error 3.25), while its own spectral
     initializer gave 0.17. For a connected low-noise graph the lift follows
     from cycle consistency, so it adds no pose information.
2. **SDR comparator** (`sdr`, Rosen et al. 2019 SE-Sync relaxation),
   evaluator-owned, on the scan experiments only, as in the paper (Table 2
   excludes SDR). Translations are eliminated in closed form. The rotation SDP
   is solved by ADMM and rounded as in SE-Sync, with weights from the declared
   noise. A public copy is in `baseline/sdr.py`.
3. **Synthetic graphs are conditioned on connectivity** (test generator,
   public generator, train evaluator). On the previous unconditioned graphs,
   77 of 150 p=0.05 trials had isolated nodes. Their placement is
   unidentifiable, so part of the score paid for guessing (see shortcuts).
4. **Evaluator gauge alignment made sign-robust (test flaw).** The paper's
   aligner `q = s/|s|`, `s = Σ q̂_j* q_j`, used a sign-fixing loop. When an
   estimate's quaternion signs split evenly against the truth
   representatives, the loop could stall orthogonal to the true alignment.
   Every node then scored ≈180° off (trial error ≈2π) while translations were
   fine. It hit EIG, SDR and the MLE refinement, whose signs come from
   rotation matrices, in 1–3% of scan trials. The stronger control scored
   −0.112 on the test before the fix and +0.0960 after it. Signs are now
   resolved by the dominant eigenvector of `Σ t t^T`, then the paper's sum is
   applied. Sign-consistent outputs score exactly as before: all 48 hidden
   reference statistics are bit-identical.
5. **Weights.** p005_noise005 0.30→0.20, p005_noise010 0.30→0.20, p008 0.25→0.15,
   p030 0.15→0.10; scan_sparse 0.20 and scan_dense 0.15 (new). Real-data
   registration is one of the paper's two empirical pillars (abstract,
   Sec. 4.3), so it now carries 35%. Sparse graphs weigh more because the
   paper stresses robustness to missing measurements. Coefficients per metric
   are unchanged (1, 0.25, 0.35, 0.2).
6. Packaging:
   - `download.sh` fetches the scans (checksummed) and the SciPy wheel used
     only by the ICP builder.
   - `setup.sh` installs SciPy.
   - `reproduce.sh` rebuilds the scan graphs if missing.
   - The obsolete `scripts/hardening_*.sh` scripts were removed.

## Does better science score higher?

The before ranks are from the previous hardening's cohort. After ranks are
hidden-test ranks of this audit's cohort: 13 candidate attempts including the
failures, normalized by their spread. Magnitudes are cohort-dependent; the
ordering and the paired intervals are the checks.

| Method | Before (prev. gym, test) | After (test) | Paired 95% interval after |
|---|---:|---:|---:|
| Reference (DQGPM) | 0 | 0 | anchor |
| Reference, seeds 1 / 2 | +3.2e‑7 / +1.1e‑7 | +4.6e‑9 / +3.0e‑9 | ±1.7e‑8 |
| Stronger: noise-aware refinement (synthetic) + SE(3) MLE refinement (scans) | +0.156 (synthetic only) | **+0.0960** | [+0.0949, +0.0970] |
| Stronger, before the alignment fix (same raw outputs) | — | −0.112 | [−0.142, −0.023] |
| Weaker: rounded DQ spectral initializer | −0.025 | **−0.0190** | [−0.0198, −0.0183] |
| Matrix EIG (evaluator comparator, as if ranked) | +0.0088 | +0.0003 | [+0.0002, +0.0004] |
| SDR (scan experiments only, as if ranked) | not run | +0.0005 | scan experiments only |

The stronger control improves both mean errors in all six experiments, e.g.
hidden p005_noise010 R/T 0.0932/0.0866 vs reference 0.1529/0.1197. Paired
improvements are 28–70% on synthetic data. On scans it gains +2.7%
(sparse rotation) and +1.5% (dense rotation), both with paired intervals
above zero. The weaker control is worse in every experiment, e.g. scan_sparse
R 0.0305 vs 0.0260. Public and hidden reference means agree within 2% on
synthetic data and within 13% (R) and 26% (T) on scans (different objects).

## Reference scores before and after

| Hidden experiment | Before R / T | After R / T | Why it changed |
|---|---|---|---|
| p005_noise005 | 0.10804 / 0.07760 | 0.07659 / 0.05953 | connected graphs only |
| p005_noise010 | 0.17940 / 0.13404 | 0.15291 / 0.11965 | connected graphs only |
| p008_noise010 | 0.11254 / 0.08669 | 0.11134 / 0.08557 | connected graphs only (few changed) |
| p030_noise010 | 0.05220 / 0.04050 | 0.05227 / 0.04092 | new instances, same distribution |
| scan_sparse | — | 0.02601 / 0.001694 | new |
| scan_dense | — | 0.01845 / 0.000902 | new |

The method code is unchanged. The reference and every baseline were rerun from
the final code on the final data (job `8544621f-ca5`), and the canonical
`scoring/scores_{train,test}.json` contain only the reference and the fixed
comparators. Paper-reported numbers are unchanged under `_paper_reported`;
Table 4 is added under `_paper_reported_table4`.

## Major shortcuts

| Shortcut | Before | Fix | After (test) |
|---|---|---|---|
| Guess identity for unidentifiable isolated nodes (hand-written rule) | Unconditioned p=0.05 graphs: translation gain +0.0051 (SE 0.0010) over the reference. Explains EIG's old +0.0088 rank (its per-component solver did this). | Synthetic graphs conditioned on connectivity | rank 0.0, identical to reference |
| Pool the 100 perturbation trials of one scan graph (average, solve once) | Native frames: error −25…−55%, e.g. bunny R 0.0326→0.0149, Armadillo-sparse R 0.0188→0.0083 | Fresh random frame per scan and random labels per trial | rank 0.0 (no two trials share a graph; reduces to the reference) |
| Hard-code the published Stanford alignment | Native frames: exactly zero error | Hidden per-trial frames and labels | failed, −7.2645 |
| All translations zero (tiny native translations) | Native frames: T 0.00128/0.00125 beats the reference's 0.00146/0.00177 on Buddha/dragon sparse | Frame translations N(0, 5 cm) per axis make translation estimation non-trivial | failed, −7.2645 |
| Rebuild public answers / one pose per instance / select trials / NaN (previously repaired) | +0.91 / +0.91 / +0.69 / invalid | unchanged protocol | all failed, −7.2645 |

"Before" for the three scan rows is `redteam/hardening2/diag_before.json`:
the same graphs and perturbations in native frames with fixed labels. That is
the naive version of the new experiment, which never shipped. Failed attempts
carry finite worst-case values in all 48 scored fields.

## Headroom check

No reference metric sits at its bound: all 48 hidden statistics are strictly
positive. The stronger control is above the reference in every experiment.

- **Synthetic experiments:** large headroom (stronger +28–70%).
- **Scan experiments:** small headroom. The best estimators tried (SDR, which
  is the global MLE here, and local MLE refinement) gain only 1.5–3%. The
  remaining error is dominated by real ICP registration error, which no
  synchronization method can remove from the measurements.
- The new experiment comes from the paper's own Table 4. No simple variant
  reaches a bound.
- Brute force does not apply: the problems are continuous and the hidden
  instances are unseen.

## Paper comparisons, stated plainly

- **Synthetic (Table 2), DQGPM vs EIG: tie.** On connected graphs the two agree
  within 0.6% in rotation (EIG marginally lower) and 1.1% in translation
  (either direction), e.g. hidden p005_noise010 R 0.1529 vs 0.1524,
  T 0.1197 vs 0.1194.
  - On the old unconditioned graphs, a per-component EIG beat DQGPM only by
    guessing isolated nodes better.
  - The paper's "largest gains on sparse graphs" plausibly come from EIG's
    instability on disconnected graphs (it trims 15% "due to EIG
    instability"). That regime is not identifiable and is no longer scored.
- **Real scans (Table 4):** DQGPM and EIG are equal to four digits on every
  object. SDR is slightly better:
  - rotation: bunny 0.0309 vs 0.0320, Armadillo-sparse 0.0180 vs 0.0190,
    Armadillo-dense 0.0154 vs 0.0160;
  - translation within ±9%.
  - The paper's "comparable best accuracy" holds. The EIG/SDR failures it
    reports (rotation error ≈3.1–3.6 on all sparse graphs) do not reproduce
    with correct implementations. Runtime, the paper's other advantage over SDR,
    is not scored.
- **Absolute synthetic errors stay far above Table 2.** Paper rotation errors
  are consistent with a rotation noise about 57× smaller than stated
  (p=0.30: 0.0005 at "5°", scaling ∝σ_r). That fits a degree-to-radian
  conversion applied twice. The gym keeps the stated noise and does not tune
  any setting toward paper numbers.
- **Dense scan graphs are sparser than the paper's** (missing 33–48% vs
  13–19%), because ICP reached the repository alignment on only about 60% of
  pairs. Sparse graphs are close: 58–69% missing vs 58–67%; bunny 66% vs 48%.

## Shortcuts and limitations left

- **Reading hidden files** (`eval/test/scans.json`, `eval/test/.raw/`) or the
  internet copy of the Stanford alignments, and then matching relative poses
  to undo the per-trial frames: this needs hidden data or hard-coded external
  answers. It is left to the attempt grader.
- **EIG (+0.0003) and SDR (+0.0005) are honest alternatives** at or slightly
  above the reference. Copying them gains about 0.3–0.5% of the stronger
  control's margin. This is an unresolved paper comparison, not a loophole.
- **The scan experiments discriminate weakly** among good methods; their
  headroom is a few percent.
- **The validator warns** that evaluator files use random generators (hidden
  instance generation and the builder). Candidates are scored only from their
  raw poses.
- **SDR solver:** the SDP is solved by ADMM, not SE-Sync's Riemannian
  staircase. It is the same relaxation, and runtime is not scored.
- **Not scored:** the theory (recovery guarantees, linear rate) and the
  runtime claims (Table 3, Table 4 timing).
