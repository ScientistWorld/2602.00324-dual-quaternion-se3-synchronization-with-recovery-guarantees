# SE(3) synchronization

Recover 100 absolute rigid poses from an incomplete graph of noisy relative
observations. Both rotation and translation must be recovered, up to one global
right gauge. Sparse graphs, noisy measurements, and poorly observed poses make
accuracy and reliability competing goals.

The gym has four synthetic settings, independent public and hidden instances,
and fixed evaluator-owned comparisons. See evaluation.md for the submission
interface and scoring rules. The hidden job performs inference and scoring;
it does not train models.
