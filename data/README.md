# Public synthetic data

`synthetic.py` independently implements the paper's 100-pose observation
model. Its public 100-trial family supports development and optional training;
it is not the hidden test family. Run `python3 -m data.synthetic --help` for
measurement-only export and optional public truth export.

No external dataset or pretrained model is needed. `scripts/download.sh`
fetches the pinned NumPy wheel from public PyPI with its published checksum
for offline package installation. Fetched packages live in data/downloads/.
All authored data-generation source is tracked here. No code here imports
method/, eval/test/, or a machine-specific data path.
