# Scoring audit

Every named case has a `run.sh` that installs its candidate artifacts, runs the
visible evaluator, then invokes `bash scripts/evaluate_test.sh` **without
arguments in a separate process**. No evaluator or Python environment is
modified. Cases restore their working artifacts and score files afterwards.

Run the complete audit on a compute node with `bash redteam/run_all.sh`.
Then run `bash redteam/run_final.sh` for the paper-aggregation diagnostics.
The final reference runs use the unmodified original implementation. An initial
vectorized pilot is retained separately and excluded from final comparisons.
All honest variants keep the reference's 100-node, 100-trial data protocol.
Shortcut implementations use only the supplied data generator, visible metric
code, public solver settings, and regenerated reference outputs.

Per-case `scores_test.json`, `scores_train.json`, and `result.json` are retained.
Large regenerated artifacts and logs stay in ignored directories. `summary.json`
contains the audit-cohort standardized ranking; its normalization is illustrative
because the eventual population of ranked future attempts is unknown.

The final findings and per-case score comparisons are in
[`../REDTEAM.md`](../REDTEAM.md). `run_record.json` records the three completed
CPU jobs. Their original logs are retained locally under ignored `.cache/jobs/`.
