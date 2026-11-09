# Final verification

Static checks pass: Python compilation, shell syntax, import separation,
independent train/test evaluators, and python3 validate.py. The first joint job
817ad207-04c passed protocol and algorithm arithmetic checks but exhausted /tmp
before the controls finished. Its zero exit code does not verify the gym.

The corrected joint check reruns reference and comparisons with a common
translation-origin output convention that preserves all relative poses. It
also runs honest stronger/weaker methods, seed controls, and repaired attacks.
Temporary inputs now stay within each evaluator's cache and are deleted per
experiment. Incomplete controls or failed science assertions stop the job.

See HARDENING.md for numerical verification once the complete check succeeds.
Synthetic recovery is the claimed scope; theoretical guarantees, real scans,
SDR, and runtime comparisons remain unverified. Unrelated pre-existing changes
to root system files and trajectory records are left untouched.
