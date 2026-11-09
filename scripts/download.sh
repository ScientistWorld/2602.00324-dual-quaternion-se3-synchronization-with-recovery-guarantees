#!/bin/bash
# No external dataset or pretrained model is required. Download the pinned
# CPython 3.11/Linux dependency (~18 MB) before offline compute jobs.
set -euo pipefail
cd /home/user
mkdir -p data/downloads/wheels
python3 - <<'PY'
import hashlib,urllib.request
from pathlib import Path
name='numpy-1.26.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl'
url='https://files.pythonhosted.org/packages/3a/d0/edc009c27b406c4f9cbc79274d6e46d634d139075492ad055e3d68445925/'+name
sha='666dbfb6ec68962c033a450943ded891bed2d54e6755e35e5835d63f4f6931d5'
path=Path('data/downloads/wheels')/name
if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
    urllib.request.urlretrieve(url,path)
assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
PY
