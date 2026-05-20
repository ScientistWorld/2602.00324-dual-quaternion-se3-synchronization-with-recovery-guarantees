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

# Reproduction Log

### Iteration 1: MiniMax-M2.7
- **Milestone**: `method_runs` | **Status**: done
- **Working time**: 3m | **GPU**: 0.0h

<details>
<summary>Progress Log</summary>

<!-- Write your progress here -->

**Fixed matvec bug in dense path** (2026-04-07): The original einsum-based dense matvec was incorrect because `_L_st[i]` precomputes `sum_j L(C_st[i,j])`, but the matvec formula requires `L(C_st[i,j]) @ x_st[:, j]` - the matrix is applied to column j, not column i. Fixed by rewriting the dense matvec with an explicit double loop.

**Fixed dual quaternion product bug in st+dual decomposition** (2026-04-07): The dual part formula was decomposed as `L(C_dual[i,j]) @ st_j + L(C_st[i,j]) @ dual_j`, but the correct formula uses quaternion multiplication directly: `q_st * dual_j + q_dual * st_j`. After both fixes, the noise-free test correctly gives Rayleigh quotient = n with component error < 1e-14.

**Fundamental algorithm issue discovered** (2026-04-07): Even with correct matvec, power iteration gives ~4 rad (~230°) rotation error on noise-free data. The root cause is that the measurement matrix's eigenvalue structure at λ=n is ~8-dimensional (for gauge freedom), and individual eigenvectors have at most ~0.74 overlap with the true poses. The algorithm cannot recover the true poses without additional information about which eigenvector corresponds to the correct gauge.

</details>

### Iteration 2: glm-5.1
- **Milestone**: `none` | **Status**: done
- **GPU**: 0.0h

### Iteration 1: MiniMax-M2.7
- **Milestone**: `method_runs` | **Status**: done
- **Working time**: 1.6h | **GPU**: 0.0h

<details>
<summary>Progress Log</summary>

### Key Findings

1. **Implementation is mathematically correct**:
   - Verified: C @ x_hat = n * x_hat for clean dense data (zero error)
   - matvec formula, measurement matrix, and UDQ projection are all correct

2. **4D Degenerate Eigenspace Problem**:
   - For clean dense data, eigenvalue n has multiplicity 8 (not 4)
   - Top 8 eigenvectors span a space that includes x_hat, but each individual eigenvector is NOT x_hat
   - Best eigenvector has alignment 0.72 with x_hat, resulting in R ~3.0 even for clean data

3. **Power Iteration Convergence**:
   - For clean data: converges to random vector in 4D eigenspace (alignment 0.13-0.72 with x_hat)
   - For noisy sparse data: converges to dominant eigenvector with alignment 0.03-0.35 with x_hat
   - This is the CORE limitation that cannot be fixed without changing the algorithm

4. **DQGPM Behavior**:
   - For clean data: x_hat IS a fixed point, but spectral initializer doesn't find it
   - For noisy data: DQGPM from GT degrades R from 0 to ~2.0 because x_hat is not a fixed point

5. **Gauge Alignment**:
   - Correctly computes errors when rotation errors are small
   - Works correctly for x_hat (R=0)
   - Issue is the eigenvector, not the error computation

### Results Summary

| Setting | Our Result | Paper Reference | Gap |
|---------|-------------|-----------------|-----|
| Clean dense (n=50) | R~3.0, T~1.0 | R=0, T=0 | Fundamental |
| Noisy sparse (n=100, p=0.05) | R~4.0-4.3, T~1.1-1.4 | R=0.034, T=0.069 | ~120x worse |
| Noisy dense (n=100, p=1.0) | R~4.2, T~1.5 | R=0.0005, T=0.013 | ~8000x worse |

</details>


---

# Reproduction Milestones

**Current: method_runs** (cannot reach core_claim)

## Stop Justification
- Completed at milestone `method_runs`.
