"""Patch-based fingerprinting for local defect detection.

ADR-IND-008: Patch architecture for local defects.
- Global fingerprint misses defects affecting <5% of points
- Solution: sample overlapping patches via FPS, fingerprint each patch
- Compare scan patches to reference patch bank (nearest neighbor)
- Aggregate: top-k mean anomaly score

Patch sampling:
1. Farthest Point Sampling (FPS) for patch centers
2. Each patch = kNN around center point
3. Overlapping patches ensure no gaps
"""

import numpy as np
from scipy.spatial.distance import cdist

from core.spectral_fingerprint import extract_fingerprint


def fps_sampling(points, n_patches, seed=42):
    """Farthest Point Sampling — selects diverse, well-distributed centers.
    
    Args:
        points: (N, 3) point cloud
        n_patches: number of patch centers to sample
        seed: random seed for deterministic starting point
    
    Returns:
        indices: array of shape (n_patches,) with center point indices
    """
    N = len(points)
    n_patches = min(n_patches, N)
    
    rng = np.random.RandomState(seed)
    indices = np.zeros(n_patches, dtype=np.int64)
    # Start from deterministic pseudo-random point
    indices[0] = rng.randint(N)
    
    dists = np.full(N, np.inf)
    
    for i in range(1, n_patches):
        # Update distances to farthest selected point
        new_dists = np.linalg.norm(points - points[indices[i-1]], axis=1)
        dists = np.minimum(dists, new_dists)
        # Select farthest point
        indices[i] = np.argmax(dists)
    
    return indices


def extract_patch(points, center_idx, patch_size=128):
    """Extract local patch around center point via kNN.
    
    Args:
        points: (N, 3) point cloud
        center_idx: index of center point
        patch_size: number of points in patch (kNN)
    
    Returns:
        patch_points: (patch_size, 3) local point cloud
        patch_indices: indices of points in original cloud
    """
    center = points[center_idx]
    dists = np.linalg.norm(points - center, axis=1)
    
    # Get kNN including center
    patch_indices = np.argsort(dists)[:patch_size]
    patch_points = points[patch_indices].copy()
    
    # Center patch at origin for scale invariance
    patch_points -= patch_points.mean(axis=0)
    
    return patch_points, patch_indices


def extract_patch_fingerprints(points, n_patches=32, patch_size=128):
    """Extract fingerprints for all patches in a point cloud.
    
    Args:
        points: (N, 3) point cloud
        n_patches: number of patches to sample
        patch_size: points per patch
    
    Returns:
        list of dicts: [{"center": idx, "indices": [...], "fingerprint": {...}}, ...]
    """
    center_indices = fps_sampling(points, n_patches)
    
    patch_data = []
    for center_idx in center_indices:
        patch_points, patch_indices = extract_patch(points, center_idx, patch_size)
        
        if len(patch_points) < 10:
            continue
        
        fp = extract_fingerprint(patch_points, k=8, k_eigen=8)
        if fp is None:
            continue
        
        patch_data.append({
            "center": int(center_idx),
            "indices": patch_indices.tolist(),
            "center_pos": points[center_idx].tolist(),
            "fingerprint": fp,
        })
    
    return patch_data


def patch_feature_vector(patch_fp):
    """Convert patch fingerprint to flat vector for NN search."""
    from core.spectral_fingerprint import feature_vector
    return feature_vector(patch_fp)


def build_patch_bank(points, n_patches=64, patch_size=128):
    """Build reference patch bank from golden scan.
    
    Returns:
        dict: {
            "points": original point cloud,
            "patches": list of patch data with fingerprints,
            "feature_matrix": (n_patches, n_features) array for fast NN,
        }
    """
    patches = extract_patch_fingerprints(points, n_patches, patch_size)
    
    if not patches:
        return None
    
    feature_matrix = np.array([patch_feature_vector(p["fingerprint"]) for p in patches])
    
    return {
        "points": points,
        "patches": patches,
        "feature_matrix": feature_matrix,
    }


def score_patches_against_bank(scan_patch_bank, ref_patch_bank):
    """Score each scan patch against nearest reference patch.
    
    Uses Euclidean distance in feature space.
    
    Returns:
        scores: array of anomaly distances per scan patch
        matched_ref_idx: index of nearest reference patch for each scan patch
    """
    ref_features = ref_patch_bank["feature_matrix"]
    scan_features = scan_patch_bank["feature_matrix"]
    
    # Pairwise distance matrix
    dist_matrix = cdist(scan_features, ref_features, metric='euclidean')
    
    # Nearest reference patch for each scan patch
    min_dists = dist_matrix.min(axis=1)
    matched_idx = dist_matrix.argmin(axis=1)
    
    return min_dists, matched_idx
