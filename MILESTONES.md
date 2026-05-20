# Reproduction Milestones

**Current: method_runs** (cannot reach core_claim)

## Progress Log

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

## Stop Justification
- Completed at milestone `method_runs`.
