# Final gym design

Measurement-only solver commands; private instances at test time; public
instances from the same procedures. Six scored experiments: four synthetic
n=100 settings on connected Erdos-Renyi graphs (paper Table 2 settings), and
two real multi-view registration settings built from pairwise ICP of Stanford
3D Scanning Repository scans (paper Sec. 4.3, Table 4), with hidden objects,
hidden per-trial rigid frames and labels, and sign-consistent measurements.
Evaluators fix all comparisons (DQ spectral, matrix EIG, SDR), recompute every
quantity from raw poses with a double-cover-robust gauge alignment, and apply
complete failure penalties before ranking. See HARDENING.md.
