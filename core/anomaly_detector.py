"""SpectralAnomalyDetector — 3-class industrial defect detection.

ADR-IND-002: Direct distance from reference + calibrated thresholds.
- Single reference mode: compare scan fingerprint to reference fingerprint
- Batch calibration mode: learn normal variation distribution

Classes:
- NORMAL: within normal variation (distance < threshold_deformed)
- DEFORMED: unusual but acceptable (threshold_deformed <= distance < threshold_anomalous)
- ANOMALOUS: extreme deviation — rescan required (distance >= threshold_anomalous)
"""

import json
import numpy as np
from .spectral_fingerprint import extract_fingerprint, feature_vector


class SpectralAnomalyDetector:
    """Detect anomalies in 3D scans using spectral + geometric fingerprinting."""
    
    CLASSES = ["NORMAL", "DEFORMED", "ANOMALOUS"]
    
    def __init__(self, k=12, k_eigen=15):
        self.k = k
        self.k_eigen = k_eigen
        self.ref_vector = None
        self.normal_mean = None
        self.normal_std = None
        self.threshold_deformed = 1.5
        self.threshold_anomalous = 4.0
        self._mode = None  # "single" or "batch"
    
    def fit_reference(self, points, threshold_deformed=1.5, threshold_anomalous=4.0):
        """Fit on a single reference scan.
        
        Simplest mode: direct distance comparison.
        Thresholds are tuned for synthetic manifolds; adjust for real parts.
        """
        fp = extract_fingerprint(points, self.k, self.k_eigen)
        if fp is None:
            raise ValueError("Failed to extract fingerprint from reference")
        self.ref_vector = feature_vector(fp)
        self.threshold_deformed = threshold_deformed
        self.threshold_anomalous = threshold_anomalous
        self._mode = "single"
        return self
    
    def calibrate(self, normal_scans, threshold_deformed=1.5, threshold_anomalous=4.0):
        """Calibrate on a batch of normal scans.
        
        Learns distribution of normal variation.
        Recommended: >= 5 scans including slight noise variants.
        """
        if len(normal_scans) < 2:
            raise ValueError(f"Need >= 2 normal scans, got {len(normal_scans)}")
        
        vectors = []
        for i, scan in enumerate(normal_scans):
            fp = extract_fingerprint(scan, self.k, self.k_eigen)
            if fp is None:
                print(f"  Warning: failed fingerprint on normal scan {i}")
                continue
            vectors.append(feature_vector(fp))
        
        if len(vectors) < 2:
            raise ValueError(f"Only {len(vectors)} valid fingerprints from {len(normal_scans)} scans")
        
        self.normal_mean = np.mean(vectors, axis=0)
        self.normal_std = np.std(vectors, axis=0)
        # ADR-IND-004: Std floor prevents overfitting to ideal scans
        min_std = np.abs(self.normal_mean) * 0.10
        self.normal_std = np.maximum(self.normal_std, min_std)
        self.normal_std = np.maximum(self.normal_std, 1e-6)
        self.threshold_deformed = threshold_deformed
        self.threshold_anomalous = threshold_anomalous
        self._mode = "batch"
        
        return self
    
    def _distance(self, fp):
        """Compute anomaly distance from reference/normal."""
        vec = feature_vector(fp)
        
        if self._mode == "single":
            return float(np.linalg.norm(vec - self.ref_vector))
        elif self._mode == "batch":
            z_scores = np.abs((vec - self.normal_mean) / self.normal_std)
            return float(np.max(z_scores))
        else:
            raise RuntimeError("Detector not fitted. Call fit_reference() or calibrate() first.")
    
    def detect(self, points):
        """Detect anomaly in a 3D scan.
        
        Returns:
            dict with keys: verdict, distance, confidence, fingerprint
        """
        fp = extract_fingerprint(points, self.k, self.k_eigen)
        if fp is None:
            return {
                "verdict": "ANOMALOUS",
                "distance": float('inf'),
                "confidence": 1.0,
                "fingerprint": None,
                "reason": "failed_fingerprint_extraction",
            }
        
        dist = self._distance(fp)
        
        if dist >= self.threshold_anomalous:
            verdict = "ANOMALOUS"
            confidence = min(1.0, (dist - self.threshold_anomalous) / 5.0 + 0.8)
        elif dist >= self.threshold_deformed:
            verdict = "DEFORMED"
            confidence = min(1.0, (dist - self.threshold_deformed) / 3.0 + 0.6)
        else:
            verdict = "NORMAL"
            confidence = min(1.0, 1.0 - dist / self.threshold_deformed)
        
        return {
            "verdict": verdict,
            "distance": round(dist, 3),
            "confidence": round(confidence, 3),
            "fingerprint": fp,
            "thresholds": {
                "deformed": self.threshold_deformed,
                "anomalous": self.threshold_anomalous,
            },
        }
    
    def save(self, path):
        """Save calibration parameters."""
        if self._mode is None:
            raise RuntimeError("Not fitted")
        data = {
            "k": self.k,
            "k_eigen": self.k_eigen,
            "mode": self._mode,
            "threshold_deformed": self.threshold_deformed,
            "threshold_anomalous": self.threshold_anomalous,
        }
        if self._mode == "single":
            data["ref_vector"] = self.ref_vector.tolist()
        elif self._mode == "batch":
            data["normal_mean"] = self.normal_mean.tolist()
            data["normal_std"] = self.normal_std.tolist()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls, path):
        """Load calibration parameters."""
        with open(path) as f:
            data = json.load(f)
        det = cls(k=data["k"], k_eigen=data["k_eigen"])
        det._mode = data["mode"]
        det.threshold_deformed = data["threshold_deformed"]
        det.threshold_anomalous = data["threshold_anomalous"]
        if det._mode == "single":
            det.ref_vector = np.array(data["ref_vector"])
        elif det._mode == "batch":
            det.normal_mean = np.array(data["normal_mean"])
            det.normal_std = np.array(data["normal_std"])
        return det
