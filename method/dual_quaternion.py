"""
Dual Quaternion Algebra for SE(3) Pose Representation.

Key concepts:
- Dual quaternions: q = q_st + q_dual * epsilon, where epsilon^2 = 0
- Unit dual quaternions represent SE(3) poses
- A pose (R, t) is represented as: x = (1 + epsilon * t / 2) * q
  where q is the unit quaternion for rotation R
"""

import numpy as np


class DualQuaternion:
    """Dual quaternion representation: q = q_st + q_dual * epsilon"""
    
    def __init__(self, q_st, q_dual):
        """
        Args:
            q_st: quaternion standard part (4-vector [w, x, y, z] or 4xN array)
            q_dual: quaternion dual part (4-vector or 4xN array)
        """
        self.q_st = np.array(q_st, dtype=np.float64)
        self.q_dual = np.array(q_dual, dtype=np.float64)
        
    @staticmethod
    def from_rotation_translation(axis, angle, translation):
        """
        Create unit dual quaternion from rotation axis, angle, and translation.
        x = (1 + epsilon * t / 2) * q
        """
        # Normalize axis
        axis = np.array(axis, dtype=np.float64)
        axis = axis / np.linalg.norm(axis)
        
        # Unit quaternion from axis-angle (q = cos(theta/2) + sin(theta/2) * axis)
        half_angle = angle / 2.0
        w = np.cos(half_angle)
        xyz = np.sin(half_angle) * axis
        
        q_st = np.array([w, xyz[0], xyz[1], xyz[2]])
        
        # Translation dual part: q_dual = (1/2) * q_st * t
        # where t is treated as a pure quaternion (0 + t), and multiplication is quaternion product
        t_quat = np.array([0.0, translation[0], translation[1], translation[2]])
        q_dual = 0.5 * quaternion_multiply(q_st, t_quat)
        
        return DualQuaternion(q_st, q_dual)
    
    @staticmethod
    def from_matrix_4x4(T):
        """
        Create unit dual quaternion from 4x4 SE(3) matrix.
        T = [R, t; 0, 1]
        """
        R = T[:3, :3]
        t = T[:3, 3]
        
        # Extract rotation axis and angle from SO(3) matrix
        trace = np.trace(R)
        if trace > 2.9999:  # Identity
            axis = np.array([0, 0, 1])
            angle = 0.0
        elif trace < -0.9999:  # 180 degree rotation
            # Find axis from diagonal
            if R[0,0] > R[1,1] and R[0,0] > R[2,2]:
                axis = np.array([1, 0, 0])
                s = np.sqrt(R[0,0] + R[1,1] + R[2,2] + 1)
            elif R[1,1] > R[2,2]:
                axis = np.array([0, 1, 0])
                s = np.sqrt(R[0,0] + R[1,1] + R[2,2] + 1)
            else:
                axis = np.array([0, 0, 1])
                s = np.sqrt(R[0,0] + R[1,1] + R[2,2] + 1)
            axis = (axis + (R[2,1] - R[1,2], R[0,2] - R[2,0], R[1,0] - R[0,1])) / (2 * s)
            angle = np.pi
        else:
            angle = np.arccos((trace - 1) / 2)
            s = 2 * np.sin(angle)
            axis = np.array([
                R[2,1] - R[1,2],
                R[0,2] - R[2,0],
                R[1,0] - R[0,1]
            ]) / s
        
        axis = axis / np.linalg.norm(axis)
        return DualQuaternion.from_rotation_translation(axis, angle, t)
    
    def conjugate(self):
        """Dual quaternion conjugate: q* = q_st* + q_dual* * epsilon"""
        return DualQuaternion(quaternion_conjugate(self.q_st),
                              quaternion_conjugate(self.q_dual))
    
    def norm_sq(self):
        """
        Square of magnitude as dual number: |q|^2 = q q* = |q_st|^2 + 2*sc(q_st, q_dual)*epsilon
        Returns a dual number tuple (standard, dual)
        """
        st_sq = np.dot(self.q_st, self.q_st)
        sc = quaternion_inner_product(self.q_st, self.q_dual)
        return st_sq + 2 * sc * np.float64(1e-10)  # Dual part
    
    def magnitude(self):
        """Magnitude as dual number"""
        return np.sqrt(np.abs(self.norm_sq()))
    
    def is_unit(self, tol=1e-8):
        """Check if dual quaternion is unit (|q| = 1)"""
        ns = self.norm_sq()
        st_val = ns[0] if hasattr(ns, '__len__') else ns
        return np.abs(st_val - 1.0) < tol
    
    def __repr__(self):
        return f"DualQuaternion(st={self.q_st}, dual={self.q_dual})"


def quaternion_conjugate(q):
    """Quaternion conjugate: q* = w - x*i - y*j - z*k"""
    return np.array([q[0], -q[1], -q[2], -q[3]])


def quaternion_multiply(p, q):
    """Quaternion multiplication p * q"""
    # p = (w1, v1), q = (w2, v2)
    # p*q = (w1*w2 - v1.v2, w1*v2 + w2*v1 + v1 x v2)
    w1, x1, y1, z1 = p[0], p[1], p[2], p[3]
    w2, x2, y2, z2 = q[0], q[1], q[2], q[3]
    
    w = w1*w2 - x1*x2 - y1*y2 - z1*z2
    x = w1*x2 + x1*w2 + y1*z2 - z1*y2
    y = w1*y2 - x1*z2 + y1*w2 + z1*x2
    z = w1*z2 + x1*y2 - y1*x2 + z1*w2
    
    return np.array([w, x, y, z])


def quaternion_inner_product(p, q):
    """Inner product sc(p* * q) = w1*w2 + v1·v2 = np.dot(p, q)."""
    return np.dot(p, q)


def quaternion_vector_action(q, v):
    """
    Apply quaternion rotation to 3D vector.
    Given unit quaternion q and vector v (as pure quaternion),
    returns rotated vector: q * v * q*
    """
    # v as pure quaternion: [0, vx, vy, vz]
    v_quat = np.array([0.0, v[0], v[1], v[2]])
    
    # q * v
    temp = quaternion_multiply(q, v_quat)
    
    # (q * v) * q*
    result = quaternion_multiply(temp, quaternion_conjugate(q))
    
    # Return vector part
    return np.array([result[1], result[2], result[3]])


def normalize_quaternion(q):
    """Normalize quaternion to unit length"""
    norm = np.linalg.norm(q)
    if norm < 1e-12:
        return q.copy()
    return q / norm


def dual_quaternion_multiply(p, q):
    """
    Dual quaternion multiplication: (p_st + p_dual*eps) * (q_st + q_dual*eps)
    = p_st*q_st + (p_st*q_dual + p_dual*q_st)*eps
    """
    st = quaternion_multiply(p.q_st, q.q_st)
    dual = quaternion_multiply(p.q_st, q.q_dual) + quaternion_multiply(p.q_dual, q.q_st)
    return DualQuaternion(st, dual)


def normalize_dual_quaternion(dq):
    """
    Normalize a dual quaternion to unit dual quaternion.
    Unit dual quaternion: x* * x = 1, which requires sc(q_st*, q_dual) = 0.
    Formula:
    If dq_st != 0:
        u_st = dq_st / |dq_st|
        u_dual = (dq_dual - dq_st * sc(dq_st*, dq_dual) / |dq_st|²) / |dq_st|
    If dq_st == 0 and dq_dual != 0:
        u_st = dq_dual / |dq_dual|
        u_dual = any quaternion with sc(u_st* * u_dual) = 0
    """
    st = dq.q_st
    dual = dq.q_dual

    st_norm_sq = np.dot(st, st)

    if st_norm_sq > 1e-12:
        st_norm = np.sqrt(st_norm_sq)
        st_normalized = st / st_norm
        # sc(q_st*, q_dual) is the dot product (scalar part of q_st* * q_dual)
        sc_val = np.dot(st, dual) / st_norm_sq
        u_dual = (dual - sc_val * st) / st_norm
        return DualQuaternion(st_normalized, u_dual)
    else:
        dual_norm = np.linalg.norm(dual)
        if dual_norm > 1e-12:
            dual_normalized = dual / dual_norm
            if abs(dual_normalized[0]) < 0.9:
                orth = np.array([0.0, 1.0, 0.0, 0.0])
            else:
                orth = np.array([0.0, 0.0, 1.0, 0.0])
            sc = quaternion_inner_product(orth, dual_normalized)
            orth = orth - sc * dual_normalized
            orth = normalize_quaternion(orth)
            return DualQuaternion(dual_normalized, orth)
        else:
            return DualQuaternion(np.array([1.0, 0.0, 0.0, 0.0]),
                                  np.array([0.0, 0.0, 0.0, 0.0]))


def dual_quaternion_norm(dq):
    """Compute ||dq||_2 as a dual number (returns (standard, dual) tuple)"""
    st_norm_sq = np.dot(dq.q_st, dq.q_st)
    sc_val = quaternion_inner_product(dq.q_st, dq.q_dual)
    return st_norm_sq + 2 * sc_val  # Dual number representation


def dual_quaternion_inner_product(dq1, dq2):
    """
    Inner product of dual quaternion vectors: sum_i x_i* y_i
    For vectors, this is the sum over all elements
    """
    st_prod = quaternion_inner_product(dq1.q_st, dq2.q_st)
    dual_prod = quaternion_inner_product(dq1.q_dual, dq2.q_dual)
    return st_prod + dual_prod  # Returns a dual number tuple


def sample_random_unit_dual_quaternion():
    """Sample a random unit dual quaternion representing a random SE(3) pose."""
    # Random rotation: uniform axis from unit sphere, angle from [0, 2π)
    axis = np.random.randn(3)
    axis = axis / np.linalg.norm(axis)
    angle = np.random.uniform(0, 2 * np.pi)
    
    # Random translation: N(0, 1) per component
    translation = np.random.randn(3)
    
    return DualQuaternion.from_rotation_translation(axis, angle, translation)


def sample_random_noise_dual_quaternion(sigma_t, sigma_r_deg):
    """
    Sample a noise dual quaternion.
    Rotation noise: axis uniform from sphere, angle from N(0, sigma_r^2)
    Translation noise: N(0, sigma_t^2) per component
    """
    axis = np.random.randn(3)
    axis = axis / np.linalg.norm(axis)
    angle = np.random.randn() * np.radians(sigma_r_deg)
    
    # Clamp angle to avoid numerical issues
    angle = np.clip(angle, -np.pi/2, np.pi/2)
    
    translation_noise = np.random.randn(3) * sigma_t
    
    return DualQuaternion.from_rotation_translation(axis, angle, translation_noise)


def dual_quaternion_to_matrix(dq):
    """
    Convert unit dual quaternion to 4x4 SE(3) matrix.
    """
    q_st = dq.q_st
    q_dual = dq.q_dual
    
    # Extract rotation quaternion
    w, x, y, z = q_st[0], q_st[1], q_st[2], q_st[3]
    
    # Rotation matrix from quaternion (Neumann projection to ensure proper rotation)
    R = np.array([
        [1 - 2*(y*y + z*z),     2*(x*y - z*w),     2*(x*z + y*w)],
        [    2*(x*y + z*w), 1 - 2*(x*x + z*z),     2*(y*z - x*w)],
        [    2*(x*z - y*w),     2*(y*z + x*w), 1 - 2*(x*x + y*y)]
    ])
    
    # Extract translation from dual part
    # q_dual = (1/2) * t * q_st
    # t * q_st = 2 * q_dual
    # We need to solve for t
    # In quaternion form: if t_quat = 2 * q_dual, then t_quat = t * q_st (quaternion multiplication)
    # t_quat = (0, t) quaternion, q_st = (w, v) quaternion
    # t * q_st = (0 * w - t.v, 0 * v + w * t + t x v)
    #          = (-t.v, w*t + t x v)
    # We have t_quat = (-t·v, w*t + t×v) = 2*q_dual
    # This is complex; let's use the direct formula from the paper:
    # x = (1 + εt/2) q => x_dual = q + (t/2)*ε*q => q_dual = (t/2) * q
    # where * is quaternion multiplication with t treated as pure quaternion
    
    # Use the formula: t = 2 * (q_dual * q_st*)
    t_quat = quaternion_multiply(q_dual, quaternion_conjugate(q_st))
    # t_quat should be (0, tx, ty, tz) since t is a pure quaternion
    # The translation is in the vector part
    t = np.array([t_quat[1], t_quat[2], t_quat[3]])
    
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    
    return T


def extract_pose_from_dual_quaternion(dq):
    """
    Extract (rotation_quaternion, translation) from unit dual quaternion.
    """
    return dq.q_st.copy(), np.array([dq.q_dual[1], dq.q_dual[2], dq.q_dual[3]])


def rotation_error(q1, q2):
    """
    Compute rotation error: d_R(q1, q2) = 2 * arccos(2 * <q1, q2>^2 - 1)
    Both quaternions should be unit quaternions.
    """
    inner = np.abs(quaternion_inner_product(q1, q2))
    inner = min(inner, 1.0)  # Clamp for numerical stability
    cos_theta = 2 * inner * inner - 1
    cos_theta = np.clip(cos_theta, -1.0, 1.0)
    return 2 * np.arccos(cos_theta)


def translation_error(t1, t2):
    """Compute translation error: ||t1 - t2||_2"""
    return np.linalg.norm(t1 - t2)
