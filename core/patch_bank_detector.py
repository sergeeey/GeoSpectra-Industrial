"""PatchBankDetector — Mode A: Registration-Free Patch Bank.

ADR-IND-018: Two-Mode Architecture — Mode A.

Principle:
  Instead of comparing patches at deterministic centers (requires registration),
  extract patches from BOTH reference and scan via FPS, then find nearest-neighbor
  matches in descriptor space. Pose invariance comes from relative geometric
  features (PCA ratios, spectral histogram) — absolute coordinates never used.

Why it works:
  - FPS sampling is pose-independent (geodesic distances on surface)
  - Patch fingerprints use scale-invariant spectral + geometric features
  - Nearest-neighbor matching in descriptor space = soft correspondence
  - No ICP needed → no registration failures → no alignment-induced FP

Limitations:
  - No exact defect localization (only global anomaly score)
  - Sensitive to non-rigid perturbations (jitter, occlusion)
  - Requires sufficient surface coverage in both scans

When to use:
  - Scan pose unknown or arbitrary
  - Speed critical (4x faster than Mode B)
  - Coarse screening acceptable
  - Rigid transforms only (rotation, translation, small scale)
"""

import json
import numpy as np
from scipy.spatial.distance import cdist

from core.spectral_fingerprint import extract_fingerprint, feature_vector
from core.patch_fingerprint import fps_sampling, extract_patch


def _extract_relative_patch_features(patch_points):
    """Extract pose-invariant features from a local patch.
    
    Uses ONLY relative geometry — no absolute coordinates.
    Features are invariant to rotation, translation, and uniform scaling.
    """
    if len(patch_points) < 10:
        return None
    
    # Center at origin
    pts = patch_points - patch_points.mean(axis=0)
    
    # Scale-normalize
    scale = np.linalg.norm(pts, axis=1).max()
    if scale < 1e-10:
        return None
    pts = pts / scale
    
    # Spectral fingerprint of the patch (scale-invariant by median normalization)
    fp = extract_fingerprint(pts, k=8, k_eigen=8)
    if fp is None:
        return None
    
    # Geometric features of the patch (scale-invariant by construction)
    cov = np.cov(pts.T)
    eigvals = np.linalg.eigvalsh(cov)
    eigvals = np.sort(eigvals)[::-1]
    eigvals = np.maximum(eigvals, 1e-10)
    
    # PCA ratios (shape descriptors, rotation invariant)
    pca_ratio_21 = eigvals[1] / eigvals[0]
    pca_ratio_32 = eigvals[2] / eigvals[1] if eigvals[1] > 0 else 0.0
    
    # Point distribution within patch
    dists_from_center = np.linalg.norm(pts, axis=1)
    dist_mean = float(np.mean(dists_from_center))
    dist_std = float(np.std(dists_from_center))
    dist_skew = float(np.percentile(dists_from_center, 75) - np.percentile(dists_from_center, 25))
    
    return {
        "spectral": fp,
        "pca_ratio_21": pca_ratio_21,
        "pca_ratio_32": pca_ratio_32,
        "dist_mean": dist_mean,
        "dist_std": dist_std,
        "dist_skew": dist_skew,
    }


def _patch_bank_feature_vector(features):
    """Convert patch features to flat vector for NN matching."""
    vec = feature_vector(features["spectral"])
    geo = np.array([
        features["pca_ratio_21"],
        features["pca_ratio_32"],
        features["dist_mean"],
        features["dist_std"],
        features["dist_skew"],
    ], dtype=np.float64)
    return np.concatenate([vec, geo])


def build_registration_free_patch_bank(points, n_patches=64, patch_size=128):
    """Build a pose-invariant patch bank from a reference point cloud."""
    center_indices = fps_sampling(points, n_patches)
    
    patches = []
    feature_vectors = []
    
    for center_idx in center_indices:
        patch_pts, patch_indices = extract_patch(points, center_idx, patch_size)
        features = _extract_relative_patch_features(patch_pts)
        if features is None:
            continue
        
        vec = _patch_bank_feature_vector(features)
        patches.append({
            "center": int(center_idx),
            "center_pos": points[center_idx].tolist(),
            "features": features,
        })
        feature_vectors.append(vec)
    
    if not patches:
        return None
    
    return {
        "points": points,
        "patches": patches,
        "feature_matrix": np.array(feature_vectors),
    }


class PatchBankDetector:
    """Mode A: Registration-Free Patch Bank anomaly detector."""
    
    VERDICTS = ["NORMAL", "DEFORMED", "ANOMALOUS", "BAD_SCAN"]
    
    def __init__(self, n_patches=64, patch_size=128,
                 top_k_ratio=0.05, threshold_deformed=1.5, threshold_anomalous=4.0):
        self.n_patches = n_patches
        self.patch_size = patch_size
        self.top_k = max(1, int(n_patches * top_k_ratio))
        self.threshold_deformed = threshold_deformed
        self.threshold_anomalous = threshold_anomalous
        
        self.cal_mean = None
        self.cal_std = None
        self._calibrated = False
        
        self.ref_patch_bank = None
        self._fitted = False
    
    def fit(self, reference_points):
        """Build patch bank from golden reference."""
        self.ref_patch_bank = build_registration_free_patch_bank(
            reference_points, n_patches=self.n_patches, patch_size=self.patch_size,
        )
        if self.ref_patch_bank is None:
            raise ValueError("Failed to build patch bank from reference")
        self._fitted = True
        self.calibrate(reference_points)
        return self
    
    def calibrate(self, reference_points, n_variants=30):
        """Calibrate thresholds on clean transformed variants."""
        if not self._fitted:
            raise RuntimeError("Must call fit() before calibrate()")
        
        scores = []
        rng = np.random.RandomState(42)
        fixed_rotations = [
            (90, 'x'), (90, 'y'), (90, 'z'),
            (180, 'x'), (180, 'y'), (180, 'z'),
            (45, 'z'), (135, 'z'), (270, 'z'),
        ]
        
        for i in range(n_variants):
            pts = reference_points.copy()
            if i < len(fixed_rotations):
                angle, axis = fixed_rotations[i]
            else:
                angle = rng.uniform(0, 360)
                axis = rng.choice(['x', 'y', 'z'])
            
            pts = self._rotate(pts, angle, axis)
            size = np.ptp(reference_points, axis=0).max()
            pts = pts + rng.uniform(-0.1, 0.1, 3) * size
            pts = pts * rng.uniform(0.95, 1.05)
            
            result = self._detect_raw(pts)
            scores.append(result["anomaly_score"])
        
        scores = np.array(scores)
        self.cal_mean = float(np.mean(scores))
        self.cal_std = float(np.std(scores))
        
        p95 = float(np.percentile(scores, 95))
        p99 = float(np.percentile(scores, 99))
        self.threshold_deformed = p95
        self.threshold_anomalous = max(p99, p95 * 1.02)
        self._calibrated = True
        return self
    
    def _rotate(self, points, angle_deg, axis='z'):
        angle = np.radians(angle_deg)
        if axis == 'x':
            R = np.array([[1,0,0],[0,np.cos(angle),-np.sin(angle)],[0,np.sin(angle),np.cos(angle)]])
        elif axis == 'y':
            R = np.array([[np.cos(angle),0,np.sin(angle)],[0,1,0],[-np.sin(angle),0,np.cos(angle)]])
        else:
            R = np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]])
        return points @ R.T
    
    def _detect_raw(self, scan_points):
        scan_bank = build_registration_free_patch_bank(
            scan_points, n_patches=self.n_patches, patch_size=self.patch_size,
        )
        if scan_bank is None or len(scan_bank["patches"]) < 3:
            return {"anomaly_score": 0.0, "min_dists": np.array([]), "n_patches": 0}
        
        ref_features = self.ref_patch_bank["feature_matrix"]
        scan_features = scan_bank["feature_matrix"]
        dist_matrix = cdist(scan_features, ref_features, metric='euclidean')
        min_dists = dist_matrix.min(axis=1)
        
        top_k_scores = np.partition(min_dists, -self.top_k)[-self.top_k:]
        return {"anomaly_score": float(np.mean(top_k_scores)), "min_dists": min_dists,
                "n_patches": len(scan_bank["patches"])}
    
    def detect(self, scan_points):
        if not self._fitted:
            raise RuntimeError("Not fitted. Call fit() first.")
        
        raw = self._detect_raw(scan_points)
        anomaly_score = raw["anomaly_score"]
        min_dists = raw["min_dists"]
        n_patches = raw["n_patches"]
        
        if n_patches < 3:
            return {"verdict": "BAD_SCAN", "confidence": 0.0, "anomaly_score": 0.0,
                    "n_patches": 0, "top_patches": [], "reason": "too_few_valid_patches"}
        
        scan_bank = build_registration_free_patch_bank(
            scan_points, n_patches=self.n_patches, patch_size=self.patch_size,
        )
        ref_features = self.ref_patch_bank["feature_matrix"]
        scan_features = scan_bank["feature_matrix"]
        dist_matrix = cdist(scan_features, ref_features, metric='euclidean')
        min_dists = dist_matrix.min(axis=1)
        matched_ref_idx = dist_matrix.argmin(axis=1)
        
        n_anomalous = int(np.sum(min_dists > self.threshold_deformed))
        td, ta = self.threshold_deformed, self.threshold_anomalous
        
        if anomaly_score >= ta:
            verdict, confidence = "ANOMALOUS", min(1.0, (anomaly_score - ta) / max(ta - td, 0.01) + 0.8)
        elif anomaly_score >= td:
            verdict, confidence = "DEFORMED", min(1.0, (anomaly_score - td) / max(ta - td, 0.01) + 0.6)
        else:
            verdict, confidence = "NORMAL", min(1.0, max(0.0, 1.0 - (anomaly_score / td) * 0.5))
        
        top_indices = np.argsort(min_dists)[-self.top_k:][::-1]
        top_patches = [{"scan_patch_idx": int(i), "matched_ref_idx": int(matched_ref_idx[i]),
                        "distance": float(min_dists[i])} for i in top_indices]
        
        return {
            "verdict": verdict, "confidence": round(confidence, 3),
            "anomaly_score": round(anomaly_score, 3), "n_patches": n_patches,
            "n_anomalous_patches": n_anomalous, "top_patches": top_patches,
            "all_scores": [float(d) for d in min_dists],
            "thresholds": {"deformed": round(td, 4), "anomalous": round(ta, 4),
                          "calibrated": self._calibrated,
                          "cal_mean": round(self.cal_mean, 4) if self.cal_mean else None,
                          "cal_std": round(self.cal_std, 4) if self.cal_std else None},
        }
    
    def save(self, path):
        if not self._fitted:
            raise RuntimeError("Not fitted")
        data = {
            "n_patches": self.n_patches, "patch_size": self.patch_size, "top_k": self.top_k,
            "threshold_deformed": self.threshold_deformed,
            "threshold_anomalous": self.threshold_anomalous,
            "ref_feature_matrix": self.ref_patch_bank["feature_matrix"].tolist(),
            "ref_patches": [{"center": p["center"], "center_pos": p["center_pos"]}
                           for p in self.ref_patch_bank["patches"]],
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls, path):
        with open(path) as f:
            data = json.load(f)
        det = cls(n_patches=data["n_patches"], patch_size=data["patch_size"],
                  top_k_ratio=data["top_k"] / data["n_patches"],
                  threshold_deformed=data["threshold_deformed"],
                  threshold_anomalous=data["threshold_anomalous"])
        det.ref_patch_bank = {"feature_matrix": np.array(data["ref_feature_matrix"]),
                             "patches": data["ref_patches"]}
        det._fitted = True
        return det
