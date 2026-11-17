#!/bin/bash
# Fetches everything the offline compute jobs need (~120 MB in total):
#   * pinned CPython 3.11/Linux wheels: numpy (~18 MB) and scipy (~36 MB,
#     nearest-neighbour search for building the ICP measurements);
#   * Stanford 3D Scanning Repository range scans (~82 MB compressed).
# The four scan sets of the paper's real-data experiment (bunny, Buddha
# standing, dragon standing, Armadillo standing) are hidden-test material and
# go only into eval/test/.raw/. Other scan sets of the same repository
# (Buddha and dragon on side/back/upright) form the public train slice in
# data/downloads/stanford/. Every fetch is idempotent and checksum-verified.
set -euo pipefail
cd /home/user
mkdir -p data/downloads/wheels data/downloads/stanford eval/test/.raw
python3 - <<'PY'
import hashlib, tarfile, urllib.request
from pathlib import Path

def fetch(url, path, sha):
    path = Path(path)
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        urllib.request.urlretrieve(url, path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sha, path

wheels = [
    ('numpy-1.26.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl',
     'https://files.pythonhosted.org/packages/3a/d0/edc009c27b406c4f9cbc79274d6e46d634d139075492ad055e3d68445925/',
     '666dbfb6ec68962c033a450943ded891bed2d54e6755e35e5835d63f4f6931d5'),
    ('scipy-1.11.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl',
     'https://files.pythonhosted.org/packages/6b/d4/d62ce38ba00dc67d7ec4ec5cc19d36958d8ed70e63778715ad626bcbc796/',
     '530f9ad26440e85766509dbf78edcfe13ffd0ab7fec2560ee5c36ff74d6269ff'),
]
for name, base, sha in wheels:
    fetch(base + name, Path('data/downloads/wheels') / name, sha)

repo = 'https://graphics.stanford.edu/pub/3Dscanrep/'
scans = [
    # hidden test (paper Table 4)
    ('bunny.tar.gz', 'a5720bd96d158df403d153381b8411a727a1d73cff2f33dc9b212d6f75455b84', 'eval/test/.raw', 'bunny/data/bun.conf'),
    ('happy/happy_stand.tar.gz', '3ae3aa54151187d1ab35e8c9082e05d4a5f2c07998a360330e31a88d20100068', 'eval/test/.raw', 'happy_stand/happyStandRight.conf'),
    ('dragon/dragon_stand.tar.gz', 'dc2ea0ea5f57396689bbeb9ae9410d18c4cdbbb3d25b69c014d668b97edd35f0', 'eval/test/.raw', 'dragon_stand/dragonStandRight.conf'),
    ('armadillo/Armadillo_scans.tar.gz', '0305894482fee00a19ab34f00c4fbff8040af99a9911b60380ad4d13bc78b5c8', 'eval/test/.raw', 'Armadillo_scans/ArmadilloStand.conf'),
    # public train slice
    ('happy/happy_side.tar.gz', '07d3e59aed79e34473570722e154d90738b93422473ba988e47d5f2f2834a6b6', 'data/downloads/stanford', 'happy_side/happySideRight.conf'),
    ('happy/happy_back.tar.gz', '583607be37542c901cc2b68edb1052a961b28496545b21953b82070baf99ed8e', 'data/downloads/stanford', 'happy_back/happyBackRight.conf'),
    ('dragon/dragon_side.tar.gz', 'c8703423bb063dc842b53edc0a38e55bbaf7c198a21c1df8c93eb94bd2522691', 'data/downloads/stanford', 'dragon_side/dragonSideRight.conf'),
    ('dragon/dragon_up.tar.gz', '44068c1b1b55192b2c101fe466e9bb14659a58d869a5bec028577bf3605aacae', 'data/downloads/stanford', 'dragon_up/dragonUpRight.conf'),
]
for rel, sha, dest, marker in scans:
    dest = Path(dest)
    archive = dest / Path(rel).name
    fetch(repo + rel, archive, sha)
    if not (dest / marker).exists():
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                target = (dest / member.name).resolve()
                if not str(target).startswith(str(dest.resolve())) or not (member.isfile() or member.isdir()):
                    raise RuntimeError(f'unsafe archive member {member.name}')
            tar.extractall(dest)
    assert (dest / marker).exists(), marker
PY
