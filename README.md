# Dual Quaternion SE(3) Synchronization with Recovery Guarantees

| This paper | Scientist World, the framework this environment belongs to |
|:---:|:---:|
| <a href="https://arxiv.org/abs/2602.00324"><img alt="This paper on arXiv" src="https://img.shields.io/badge/arXiv-2602.00324-b31b1b?logo=arxiv&logoColor=white"></a> | <a href="https://arxiv.org/abs/2611.08478"><img alt="Scientist World on arXiv" src="https://img.shields.io/badge/arXiv-2611.08478-b31b1b?logo=arxiv&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world"><img alt="Scientist World code" src="https://img.shields.io/badge/Code-Scientist_World-181717?logo=github&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world_cli"><img alt="Command line code" src="https://img.shields.io/badge/Code-Command_line-181717?logo=github&logoColor=white"></a> |

| | |
|---|---|
| **Paper ID** | [2602.00324](https://arxiv.org/abs/2602.00324) |

## Summary

This paper studies synchronization over `SE(3)`: recovering absolute 3D poses from noisy relative transformations. The reproduction implements the paper's unit-dual-quaternion pipeline: spectral power initialization followed by DQGPM refinement with elementwise projection onto valid poses.

## Problem

Can a synchronization method recover globally consistent absolute poses with
low rotation and translation error when many pairwise measurements are missing
and the available measurements are noisy?

## The paper's method

The paper formulates `SE(3)` synchronization directly over unit dual
quaternions and uses a two-stage solver with recovery guarantees.

## Run it

```bash
pip install sciworld
sw research 2602.00324 --mode innovate --agent claude-code
sw evaluate 2602.00324
```

## More

The full problem statement, method notes, evaluation protocol and reproduction log are in [DETAILS.md](DETAILS.md).

