# Scoring audit

Every named case has a `run.sh` that installs its candidate artifacts, runs the
visible evaluator, then invokes `bash scripts/evaluate_test.sh` **without
arguments in a separate process**. No evaluator or Python environment is
modified. Cases restore their working artifacts and score files afterwards.

Run the complete audit on a compute node with `bash redteam/run_all.sh`.
The original solver's repeated matrix products are vectorized without changing
its equations; the audit records agreement with the original implementation.
All honest variants keep the reference's 100-node, 100-trial data protocol.
Shortcut implementations use only the supplied data generator, visible metric
code, public solver settings, and regenerated reference outputs.

Per-case `scores_test.json`, `scores_train.json`, and `result.json` are retained.
Large regenerated artifacts and logs stay in ignored directories. `summary.json`
contains the audit-cohort standardized ranking; its normalization is illustrative
because the eventual population of ranked future attempts is unknown.
