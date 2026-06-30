"""
Spectral fingerprinting core — scale-invariant version.

point cloud → kNN graph → Laplacian → eigenvalues → fingerprint
"""
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh
from sklearn.neighbors import kneighbors_graph


def build_knn_graph_laplacian(points, k=12, normalized=True):
    """Build normalized kNN graph Laplacian from 3D points."""
    adj = kneighbors_graph(points, n_neighbors=min(k, len(points)-1),
                           mode='connectivity', include_self=False)
    if normalized:
        deg = np.array(adj.sum(axis=1)).flatten()
        deg_inv_sqrt = sparse.diags(1.0 / np.sqrt(deg + 1e-10))
        lap = sparse.eye(len(points)) - deg_inv_sqrt @ adj @ deg_inv_sqrt
    else:
        deg = sparse.diags(np.array(adj.sum(axis=1)).flatten())
        lap = deg - adj
    return lap


def extract_fingerprint(laplacian, k_eigen=15):
    """Extract scale-invariant spectral fingerprint.
    
    Returns dict with:
    - density: 15-bin normalized spectral density
    - r: mean consecutive spacing ratio
    - cv: coefficient of variation
    """
    n0 = laplacian.shape[0]
    k = min(k_eigen, n0 - 2)
    try:
        ev = eigsh(laplacian, k=k, which="SM", return_eigenvectors=False, tol=1e-8)
    except Exception:
        return None
    ev = np.sort(np.real(ev))
    ev = ev[ev > 1e-10]
    if len(ev) < 5:
        return None
    
    # Scale-invariant: normalize by median
    ev_norm = ev / np.median(ev)
    dens, _ = np.histogram(ev_norm, bins=15, density=True)
    
    # r-statistic (level spacing ratio)
    ratios = []
    for i in range(1, len(ev)-1):
        sm, sp = ev[i]-ev[i-1], ev[i+1]-ev[i]
        if max(sm, sp) > 0:
            ratios.append(min(sm, sp) / max(sm, sp))
    r = float(np.mean(ratios)) if ratios else 0.0
    
    # Coefficient of variation
    cv = float(np.std(ev) / np.mean(ev)) if np.mean(ev) > 0 else 0
    
    return {"density": dens.tolist(), "r": r, "cv": cv}


def fingerprint_distance(fp1, fp2, weights=(0.5, 0.3, 0.2)):
    """Weighted distance between two fingerprints.
    
    weights: (density, r, cv)
    """
    if fp1 is None or fp2 is None:
        return 1.0
    
    d1, d2 = np.array(fp1["density"]), np.array(fp2["density"])
    dist_dens = float(np.sum(np.abs(d1 - d2)) / 2.0) if len(d1) == len(d2) else 1.0
    dist_r = abs(fp1["r"] - fp2["r"])
    dist_cv = abs(fp1["cv"] - fp2["cv"])
    
    w = weights
    return w[0] * dist_dens + w[1] * dist_r + w[2] * dist_cv
