# Public data

`synthetic.py` independently implements the paper's 100-pose synthetic
observation model (graphs conditioned on connectivity). Its public 100-trial
family supports development and optional training; it is not the hidden test
family. Run `python3 -m data.synthetic --help` for measurement-only export and
optional public truth export.

Public real-scan development data: `scripts/download.sh` fetches Stanford 3D
Scanning Repository scan sets (Buddha and dragon scanned on their side, back
and upright) into `data/downloads/stanford/`. Their pairwise ICP measurement
graphs and repository alignments are committed in `eval/train/scans.json`
(built by `eval/train/build_scans.py`); the train evaluator turns them into
perturbed trials in random frames. The hidden test uses other scan sets, which
are fetched only into `eval/test/.raw/`.

`scripts/download.sh` also fetches the pinned NumPy and SciPy wheels from
public PyPI with their published checksums for offline installation. Fetched
files live in data/downloads/. All authored data-generation source is tracked.
No code here imports method/, eval/test/, or a machine-specific data path.
