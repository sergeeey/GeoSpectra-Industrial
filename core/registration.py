"""3D Registration module — align scan to reference before patch comparison.

ADR-IND-013: Registration gate before patch-based anomaly detection.

Pipeline:
1. Normalize (center + scale)
2. PCA coarse alignment (principal axes matching)
3. ICP fine alignment (point-to-point)
4. Registration quality assessment
5. Gate: if quality < threshold → REGISTRATION_FAILED

Without registration: patch detector produces 100% false positives
on rotated/translated scans (ADR-IND-012).
"""

import numpy as np
from scipy.spatial.distance import cdist
from scipy.spatial import cKDTree


def normalize_pointcloud(points):
    """Center and unit-scale a point cloud."""
    pts = points.copy()
    center = pts.mean(axis=0)
    pts -= center
    scale = np.linalg.norm(pts, axis=1).max()
    if scale > 0:
        pts /= scale
    return pts, center, scale


def pca_basis(points):
    """Compute PCA basis (principal axes) of a point cloud."""
    centered = points - points.mean(axis=0)
    cov = np.cov(centered.T)
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]
    if np.linalg.det(eigvecs) < 0:
        eigvecs[:, 2] *= -1
    return eigvecs.T, eigvals


def align_by_pca(reference, scan):
    """Coarse alignment using PCA principal axes."""
    ref_norm, ref_center, ref_scale = normalize_pointcloud(reference)
    scan_norm, scan_center, scan_scale = normalize_pointcloud(scan)
    
    ref_basis, _ = pca_basis(ref_norm)
    scan_basis, _ = pca_basis(scan_norm)
    
    best_R = None
    best_chamfer = float('inf')
    
    for sx in [-1, 1]:
        for sy in [-1, 1]:
            for sz in [-1, 1]:
                flipped_basis = scan_basis.copy()
                flipped_basis[0] *= sx
                flipped_basis[1] *= sy
                flipped_basis[2] *= sz
                
                if np.linalg.det(flipped_basis) < 0:
                    continue
                
                R_candidate = flipped_basis.T @ ref_basis
                aligned = scan_norm @ R_candidate
                
                dist = chamfer_distance(ref_norm, aligned)
                if dist < best_chamfer:
                    best_chamfer = dist
                    best_R = R_candidate
    
    aligned_scan = (scan - scan_center) @ best_R + ref_center
    return aligned_scan, best_R, ref_center - best_R.T @ scan_center


def chamfer_distance(points_a, points_b):
    """Compute Chamfer distance between two point clouds."""
    tree_b = cKDTree(points_b)
    dists_a_to_b, _ = tree_b.query(points_a, k=1)
    
    tree_a = cKDTree(points_a)
    dists_b_to_a, _ = tree_a.query(points_b, k=1)
    
    return np.mean(dists_a_to_b) + np.mean(dists_b_to_a)


def icp_point_to_point(reference, scan, max_iterations=20, tolerance=1e-6):
    """ICP point-to-point registration."""
    aligned = scan.copy()
    R_total = np.eye(3)
    t_total = np.zeros(3)
    
    prev_error = float('inf')
    converged = False
    
    for iteration in range(max_iterations):
        tree_ref = cKDTree(reference)
        distances, indices = tree_ref.query(aligned, k=1)
        
        matched_ref = reference[indices]
        
        R, t = compute_rigid_transform(aligned, matched_ref)
        
        aligned = aligned @ R.T + t
        
        R_total = R @ R_total
        t_total = R @ t_total + t
        
        rmse = np.sqrt(np.mean(distances**2))
        if abs(prev_error - rmse) < tolerance:
            converged = True
            break
        prev_error = rmse
    
    return aligned, R_total, t_total, prev_error, converged


def compute_rigid_transform(source, target):
    """Compute optimal rigid transform (R, t) via Kabsch algorithm."""
    source_center = source.mean(axis=0)
    target_center = target.mean(axis=0)
    
    source_centered = source - source_center
    target_centered = target - target_center
    
    H = source_centered.T @ target_centered
    
    U, S, Vt = np.linalg.svd(H)
    
    R = Vt.T @ U.T
    
    if np.linalg.det(R) < 0:
        Vt[2, :] *= -1
        R = Vt.T @ U.T
    
    t = target_center - source_center @ R.T
    
    return R, t


def registration_quality(reference, aligned_scan):
    """Assess registration quality."""
    tree_ref = cKDTree(reference)
    distances, _ = tree_ref.query(aligned_scan, k=1)
    
    rmse = float(np.sqrt(np.mean(distances**2)))
    chamfer = float(chamfer_distance(reference, aligned_scan))
    
    ref_scale = np.ptp(reference, axis=0).max()
    normalized_rmse = rmse / ref_scale if ref_scale > 0 else rmse
    
    overlap_ratio = float(np.mean(distances < 2 * rmse)) if rmse > 0 else 0.0
    inlier_ratio = float(np.mean(distances < 3 * rmse)) if rmse > 0 else 0.0
    
    if normalized_rmse < 0.01:
        status = "PASS"
        confidence = min(1.0, 1.0 - normalized_rmse / 0.01)
    elif normalized_rmse < 0.03:
        status = "MARGINAL"
        confidence = min(1.0, 1.0 - (normalized_rmse - 0.01) / 0.02)
    else:
        status = "FAIL"
        confidence = max(0.0, 1.0 - normalized_rmse / 0.05)
    
    return {
        "rmse": rmse,
        "normalized_rmse": normalized_rmse,
        "chamfer": chamfer,
        "overlap_ratio": overlap_ratio,
        "inlier_ratio": inlier_ratio,
        "status": status,
        "confidence": round(confidence, 3),
    }


def align_scan_to_reference(reference, scan, use_icp=True):
    """Full alignment pipeline: normalize → PCA coarse → ICP fine → quality check."""
    pca_aligned, R_pca, t_pca = align_by_pca(reference, scan)
    
    if use_icp:
        icp_aligned, R_icp, t_icp, rmse, converged = icp_point_to_point(
            reference, pca_aligned, max_iterations=30
        )
        
        R_total = R_icp @ R_pca
        t_total = R_icp @ t_pca + t_icp
    else:
        icp_aligned = pca_aligned
        R_total = R_pca
        t_total = t_pca
    
    quality = registration_quality(reference, icp_aligned)
    
    return icp_aligned, quality, R_total, t_total
