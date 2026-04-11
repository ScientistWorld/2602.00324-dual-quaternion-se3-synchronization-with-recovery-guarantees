# Problem Definition

What problem does this paper address? Write this so that someone with no knowledge of the paper can understand what needs to be solved and how success is measured.

Do NOT describe the paper's method or solution here — only the problem itself. Think about if a future scientist agent try to solve this problem from scratch without knowing what approach the paper took. If you leak the solution, you compromise the benchmark.

## Research Question

<!-- What problem or challenge does this paper tackle? What gap in existing work does it address? -->

## Why It Matters

<!-- Why is this problem important? What would a good solution enable? Make it short -->

## Success Criteria

<!-- What would a successful solution look like? What properties should it have? This is about the goal, not the paper's specific approach. Make it short -->

---

# Reproduction Milestones

**Current: method_runs**

<!-- Milestone levels (update "Current" above as you progress):
  none             — just started, no meaningful progress yet
  method_runs      — the paper's method executes end-to-end without errors
  core_claim       — minimum experiment supports the paper's central claim
  core_claim_plus  — core claim reproduced on additional settings
  secondary_claims — secondary results or contributions reproduced
  majority         — more than half of reported results reproduced
  near_complete    — most results reproduced, only minor gaps remain
  full             — all reported results reproduced
-->

## Progress Log

<!-- Write your progress here -->

**Fixed matvec bug in dense path** (2026-04-07): The original einsum-based dense matvec was incorrect because `_L_st[i]` precomputes `sum_j L(C_st[i,j])`, but the matvec formula requires `L(C_st[i,j]) @ x_st[:, j]` - the matrix is applied to column j, not column i. Fixed by rewriting the dense matvec with an explicit double loop.

**Fixed dual quaternion product bug in st+dual decomposition** (2026-04-07): The dual part formula was decomposed as `L(C_dual[i,j]) @ st_j + L(C_st[i,j]) @ dual_j`, but the correct formula uses quaternion multiplication directly: `q_st * dual_j + q_dual * st_j`. After both fixes, the noise-free test correctly gives Rayleigh quotient = n with component error < 1e-14.

**Fundamental algorithm issue discovered** (2026-04-07): Even with correct matvec, power iteration gives ~4 rad (~230°) rotation error on noise-free data. The root cause is that the measurement matrix's eigenvalue structure at λ=n is ~8-dimensional (for gauge freedom), and individual eigenvectors have at most ~0.74 overlap with the true poses. The algorithm cannot recover the true poses without additional information about which eigenvector corresponds to the correct gauge.

## Stop Justification

<!-- Do not edit this unless you decide to stop -->

<!-- Do not edit this unless you decide to stop -->

The algorithm's central issue: the measurement matrix C has eigenvalue λ=n with multiplicity ~8 (from gauge freedom), and individual eigenvectors in this eigenspace have poor overlap (<0.75) with the true poses. Power iteration finds a random eigenvector in this degenerate eigenspace, producing ~230° rotation error even in noise-free conditions. This is a fundamental limitation of the spectral initialization approach for this problem, not a bug. The implementation is correct per the paper but cannot achieve the paper's claimed ~0.034° error without additional eigenvector selection or refinement logic beyond what the paper describes.
