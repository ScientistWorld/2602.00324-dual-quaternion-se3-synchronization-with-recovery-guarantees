"""Exact reference equations with cached real block matrix multiplication."""
from __future__ import annotations

import numpy as np


def install():
    from method import sync

    original = getattr(sync.MeasurementMatrix, '_audit_original_matvec', sync.MeasurementMatrix.matvec)
    sync.MeasurementMatrix._audit_original_matvec = original

    def matvec(self, x):
        if not hasattr(self, "_audit_standard"):
            n = self.n
            self._audit_standard = np.zeros((4 * n, 4 * n))
            self._audit_dual = np.zeros((4 * n, 4 * n))
            for i, neighbors in enumerate(self.neighbors):
                for j in neighbors:
                    self._audit_standard[4*i:4*i+4, 4*j:4*j+4] = sync.left_mul_matrix(self.c_st[:, i, j])
                    self._audit_dual[4*i:4*i+4, 4*j:4*j+4] = sync.left_mul_matrix(self.c_dual[:, i, j])
        n4 = 4 * self.n
        return np.concatenate((
            self._audit_standard @ x[:n4],
            self._audit_standard @ x[n4:] + self._audit_dual @ x[:n4],
        ))

    sync.MeasurementMatrix.matvec = matvec
    return original
