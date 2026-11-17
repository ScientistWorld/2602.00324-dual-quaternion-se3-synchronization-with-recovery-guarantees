# Verification status

Final hardening (2026-11-17). Job `8544621f-ca5` built nothing new (the scan
graphs were built in `f93ae350-634`) and ran the whole audit cohort through
both evaluators from final code: reference, DQ spectral, matrix EIG, SDR, two
seed controls, stronger and weaker controls, and nine shortcut probes. Job
`5b98f5bd-c2d` applied the evaluator-only alignment fix by rescoring every
saved raw output (input fingerprints checked, nothing rerun), regenerated the
canonical reference-only score files, froze `scoring/reference.json`, and
passed `validate.py --compare --post-design` and `validate.py
--post-reproducer` (exit 0). The validator's only warnings are the heuristic
notes about random generators in evaluator files (hidden instance generation
and the ICP builder).

Verified: stronger > reference > weaker on the hidden test with paired
intervals far outside seed variation; every shortcut probe fails or ties;
no reference statistic at its bound; train and test reference means agree
(synthetic within 2%, scans within 26% on different objects).
Not reproduced: DQGPM's superiority over matrix EIG (tie) and EIG/SDR failure
on sparse scan graphs (SDR is slightly more accurate than DQGPM). See
HARDENING.md and `redteam/hardening2/report.json`.
