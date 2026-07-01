"""Spectral fingerprinting for 3D point clouds — GeoSpectra Industrial.

ADR-IND-001: Two-feature architecture.
- SPECTRAL features (density + r-stat + cv): detect scan noise, global anomalies
- GEOMETRIC features (PCA ratios, bbox ratios, asymmetry): detect local deformations

Why two? Spectral features alone miss local defects (bulge, dent, twist)
that preserve global spectrum. Geometric features catch shape changes
that spectral features miss. Together: FNR < 5% target.
"""

import numpy as np
from scipy.sparse.linalg import eigsh
from sklearn.neighbors import kneighbors_graph


def build_knn_graph_laplacian(points, k=12, normalized=True):
    """Build symmetric normalized kNN graph Laplacian."""
    adj = kneighbors_graph(points, n_neighbors=k, mode='connectivity',
                           include_self=False)
    adj = adj.maximum(adj.T)
    deg = np.array(adj.sum(axis=1)).flatten()
    if normalized:
        deg_inv_sqrt = np.power(deg, -0.5, where=deg > 0)
        deg_inv_sqrt[np.isinf(deg_inv_sqrt)] = 0
        D_inv_sqrt = np.diag(deg_inv_sqrt)
        I = np.eye(len(deg))
        L = I - D_inv_sqrt @ adj.toarray() @ D_inv_sqrt
        from scipy.sparse import csr_matrix
        L = csr_matrix(L)
    else:
        from scipy.sparse import csr_matrix, diags
        L = diags(deg) - adj
    return L


def extract_spectral_features(points, k=12, k_eigen=15):
    """Extract spectral fingerprint: scale-invariant eigenvalue features.
    
    Features:
    - density: 15-bin normalized histogram of median-normalized eigenvalues
    - r: mean consecutive spacing ratio (level repulsion, universal)
    - cv: coefficient of variation (std/mean of eigenvalues)
    
    Scale-invariant: eigenvalues normalized by median before density.
    """
    L = build_knn_graph_laplacian(points, k=k, normalized=True)
    try:
        ev = eigsh(L, k=min(k_eigen + 1, points.shape[0] - 2),
                   which='SM', return_eigenvectors=False, tol=1e-8)
    except Exception:
        return None
    ev = np.sort(np.real(ev))
    ev = ev[ev > 1e-10]
    if len(ev) < 5:
        return None
    
    ev_norm = ev / np.median(ev)
    dens, _ = np.histogram(ev_norm, bins=15, density=True)
    
    spacings = np.diff(ev_norm)
    ratios = []
    for i in range(len(spacings) - 1):
        sm, la = sorted([spacings[i], spacings[i + 1]])
        ratios.append(sm / la if la > 0 else 0.0)
    r = float(np.mean(ratios)) if ratios else 0.0
    cv = float(np.std(ev) / np.mean(ev)) if np.mean(ev) > 0 else 0.0
    
    return {"density": dens.tolist(), "r": r, "cv": cv}


def extract_geometric_features(points):
    """Extract geometric shape features: local deformations.
    
    Features (scale-invariant by construction):
    - pca_ratio_21: ratio of 2nd to 1st PCA eigenvalue (elongation)
    - pca_ratio_32: ratio of 3rd to 2nd PCA eigenvalue (flatness)
    - pca_ratio_31: ratio of 3rd to 1st PCA eigenvalue (compactness)
    - bbox_ratio_21: bounding box aspect ratio y/x
    - bbox_ratio_32: bounding box aspect ratio z/y
    - centroid_rms: RMS distance from centroid (size-normalized)
    - asymmetry_x: asymmetry along principal axis
    
    Why: spectral features miss local defects (bulge, dent, twist).
    Geometric features catch shape changes that preserve spectrum.
    """
    if len(points) < 10:
        return None
    
    # PCA
    centered = points - points.mean(axis=0)
    cov = np.cov(centered.T)
    eigvals = np.linalg.eigvalsh(cov)
    eigvals = np.sort(eigvals)[::-1]
    eigvals = np.maximum(eigvals, 1e-10)
    
    # Bounding box
    bbox = np.ptp(points, axis=0)
    bbox = np.maximum(bbox, 1e-10)
    
    # Centroid distance
    centroid = points.mean(axis=0)
    dists = np.linalg.norm(points - centroid, axis=1)
    
    # Asymmetry: difference between + and - along principal axis
    pca_axis = np.linalg.eigh(cov)[1][:, -1]  # principal axis
    projections = centered @ pca_axis
    asymmetry = float(abs(np.percentile(projections, 95) + np.percentile(projections, 5)))
    
    return {
        "pca_ratio_21": float(eigvals[1] / eigvals[0]),
        "pca_ratio_32": float(eigvals[2] / eigvals[1]),
        "pca_ratio_31": float(eigvals[2] / eigvals[0]),
        "bbox_ratio_21": float(bbox[1] / bbox[0]),
        "bbox_ratio_32": float(bbox[2] / bbox[1]),
        "bbox_ratio_31": float(bbox[2] / bbox[0]),
        "centroid_rms": float(np.mean(dists) / np.std(dists)) if np.std(dists) > 0 else 0.0,
        "asymmetry": asymmetry / (np.mean(dists) + 1e-10),
    }


def extract_fingerprint(points, k=12, k_eigen=15):
    """Full fingerprint: spectral + geometric features.
    
    Returns dict with both feature sets, or None if extraction fails.
    """
    spectral = extract_spectral_features(points, k=k, k_eigen=k_eigen)
    geometric = extract_geometric_features(points)
    if spectral is None or geometric is None:
        return None
    return {"spectral": spectral, "geometric": geometric}


def feature_vector(fp):
    """Convert fingerprint to flat numpy vector for ML."""
    spec = fp["spectral"]
    geo = fp["geometric"]
    vec = []
    vec.extend(spec["density"])
    vec.append(spec["r"])
    vec.append(spec["cv"])
    vec.extend([
        geo["pca_ratio_21"], geo["pca_ratio_32"], geo["pca_ratio_31"],
        geo["bbox_ratio_21"], geo["bbox_ratio_32"], geo["bbox_ratio_31"],
        geo["centroid_rms"], geo["asymmetry"],
    ])
    return np.array(vec, dtype=np.float64)
