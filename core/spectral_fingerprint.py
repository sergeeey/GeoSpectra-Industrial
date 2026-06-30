"""
Spectral fingerprinting core — extracted from GeoSpectra research.

Builds spectral fingerprint from 3D point cloud:
point cloud → kNN graph → Laplacian → eigenvalues → fingerprint
"""
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh


def build_knn_graph_laplacian(points, k=12, normalized=True):
    """Build normalized kNN graph Laplacian from 3D points."""
    from sklearn.neighbors import kneighbors_graph
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
    """Extract spectral fingerprint from Laplacian.
    
    Returns dict with:
    - density: 5-bin spectral density histogram
    - mean, std: eigenvalue statistics
    - r: mean consecutive spacing ratio
    - ev: eigenvalue list
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
    
    dens, _ = np.histogram(ev, bins=5, density=True)
    
    # r-statistic (mean consecutive spacing ratio)
    if len(ev) > 2:
        ratios = []
        for i in range(1, len(ev)-1):
            sm, sp = ev[i]-ev[i-1], ev[i+1]-ev[i]
            if max(sm, sp) > 0:
                ratios.append(min(sm, sp) / max(sm, sp))
        r = float(np.mean(ratios)) if ratios else 0.0
    else:
        r = 0.0
    
    return {
        "density": dens.tolist(),
        "mean": float(np.mean(ev)),
        "std": float(np.std(ev)),
        "r": r,
        "ev": ev.tolist()
    }


def spectral_distance(fp1, fp2):
    """L1 distance between two spectral fingerprints."""
    if fp1 is None or fp2 is None:
        return 1.0
    d1 = np.array(fp1["density"])
    d2 = np.array(fp2["density"])
    if len(d1) != len(d2):
        return 1.0
    return float(np.sum(np.abs(d1 - d2)) / 2.0)
