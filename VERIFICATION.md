# Verification Report

## Initial Assessment
The workspace claimed `core_claim`. The retained synthetic artifacts and implementation were usable, and the method matched the paper's dual-quaternion synchronization pipeline closely enough for a narrow core-claim reproduction. The package still needed cleanup before serving as a gym: the main scores were stale after metric schema changes, some from-scratch-facing documentation leaked method details, and the reusable data interface was incomplete.

## Issues Found
- Minor: `scoring/scores.json` was stale and did not include the declared p90/max stability metrics.
- Minor: strict method-agnostic files referenced the paper's method, baseline family, and implementation details.
- Minor: synthetic data generation was only available through the solution code, which weakened from-scratch usability.
- Minor: stale ignored checkpoint artifacts could be picked up by the default evaluator glob.
- Minor: `validate.py --compare --post-reproducer` reports warnings for train/test evaluators because they reconstruct benchmark truth from artifact seeds; manual inspection confirms those evaluators read submitted estimates from artifacts and do not call `method/`.

## Fixes Applied
- Updated `eval/evaluate.py` to compute all declared metrics without a NumPy runtime dependency and refreshed `scoring/scores.json` from the retained artifacts.
- Rewrote `briefing/problem.md`, `briefing/evaluation.md`, and `scoring/EXPERIMENTS.md` to describe the task and metrics without leaking architecture, algorithm, loss, or training details.
- Tightened `scoring/TARGETS.md`, `scoring/CONSTRAINTS.md`, and `scoring/DIRECTION.md` so they guide future work without prescribing the reproduced method.
- Added `data/synthetic.py` and `data/README.md` as a method-independent synthetic benchmark interface.
- Removed stale generated checkpoint JSON files that were not part of the retained core-claim experiments.
- Re-ran `scripts/evaluate.sh`, `python3 validate.py --compare --post-reproducer`, syntax checks, and import-separation checks.

## Final Judgment
The workspace is ready to serve as a narrow synthetic research gym. A future agent can use the method implementation in improve mode, or use the method-agnostic problem, data, and evaluation files in from-scratch mode. The main limitation is scope: the reproduction covers two sparse synthetic settings and a local spectral baseline, not the paper's full table or external matrix baselines.

- Milestone: core_claim
- Ready for gym use: yes
- Confidence: medium
- Key limitation: synthetic-only core claim on two sparse settings with absolute errors still worse than the paper's reported values.
