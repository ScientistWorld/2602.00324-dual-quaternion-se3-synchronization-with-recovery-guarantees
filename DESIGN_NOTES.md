# Design Notes

Checked the train/test split, evaluator scripts, scoring metadata, and common leakage/gaming failure modes. The split remains a fixed even/odd partition of sorted trial seeds, which keeps train and held-out test at comparable difficulty while preventing direct tuning to the exact scored trials.

Changes made:
- Fixed a shortcut where `eval/train/` and `eval/test/` trusted method-authored `truth` records in result artifacts. Both evaluators now reconstruct deterministic synthetic ground truth from each trial seed and only score the method-authored `estimate`.
- Added `error_R_max` and `error_T_max` to both split evaluators and `scoring/reference.json` so the score penalizes isolated catastrophic failures in addition to mean, standard deviation, and p90 errors.
- Added the required `description` field to all nonzero metrics in `scoring/reference.json`.
- Filtered split scoring to experiments listed in `scoring/reference.json`, so default checkpoint discovery does not emit unranked phantom experiments from leftover artifacts such as exploratory settings.
- Confirmed `scripts/evaluate_train.sh` targets `eval/train/` and `scoring/scores_train.json`, while `scripts/evaluate_test.sh` targets `eval/test/` and `scoring/scores_test.json`.
- Confirmed no `scoring/scores_train.json` or `scoring/scores_test.json` stubs are present.

Static validation performed:
- `bash -n scripts/evaluate_train.sh`
- `bash -n scripts/evaluate_test.sh`
- `python3 -m json.tool scoring/reference.json`
- Grepped for train/test cross-imports, hardcoded `METHOD_NAME`, paper-agreement metric names, and score-path copy-paste errors.

Runtime concerns for the next runner iteration:
- The deterministic ground-truth reconstruction duplicates the seeded pose-generation logic used by `method/sync.py`. The runner should verify on existing artifacts that reconstructed truth matches the original generated truth to numerical tolerance.
- The max-error metrics may be noisy if very few trials are produced. They are weighted lower than mean and p90 metrics, but the runner should watch for instability when `TRIALS` is small.
- `scripts/run.sh` currently runs the original reproduction path rather than the new train/test split. That file was out of scope for this design pass; use `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` directly for split scoring unless a later iteration wires them into the main run flow.

## Runner Outcome

Job `c0dfd92d-508` completed successfully and produced `scoring/scores_train.json`
and `scoring/scores_test.json`. Both slices contain all three reference
experiments (`p005_noise005`, `p005_noise010`, `p030_noise010`) and the same
method set (`dqgpm`, `dq_spectral`, `eig`) with no null or missing metric values.

The train/test split is not byte-identical: DQGPM mean translation error is
0.1421/0.1270 on `p005_noise005`, 0.2492/0.2289 on `p005_noise010`, and
0.0784/0.0701 on `p030_noise010` for train/test respectively. These gaps are
modest and comparable across the proposed method and baselines, so the split is
calibrated enough to detect visible-slice shortcutting without creating a
large distribution collapse.

One harness robustness fix was added after reviewing the results: the default
artifact discovery in `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh`
now searches both `checkpoints/` and `outputs/`, while still scoring every
discovered method through the same artifact interface.
