# Problem Definition

Recover absolute 3D rigid poses from noisy pairwise relative pose measurements.
The unknowns are `n` elements of `SE(3)`, each with a rotation and translation.
The observations are an incomplete graph of relative transformations between
pairs of nodes, corrupted by rotation and translation noise.

## Research Question

Can a synchronization method recover globally consistent absolute poses with
low rotation and translation error when many pairwise measurements are missing
and the available measurements are noisy?

## Why It Matters

This is a core primitive for pose-graph optimization, SLAM, structure from
motion, and multi-scan point-set registration. Better synchronization improves
global alignment before downstream registration or mapping steps.

## Success Criteria

A successful method produces valid `SE(3)` poses for every node and, after
global gauge alignment, has lower mean rotation and translation error than a
benchmark baseline under the same graph, noise, and trial settings.
