"""
Anomaly detector for industrial defectoscopy.

Compares spectral fingerprint of test part against reference (normal part).
Returns anomaly score and verdict.
"""
from .spectral_fingerprint import extract_fingerprint, spectral_distance, build_knn_graph_laplacian


class SpectralAnomalyDetector:
    """Detects anomalies in 3D scans by spectral fingerprint comparison."""
    
    def __init__(self, k_neighbors=12, k_eigen=15, threshold_normal=0.3, threshold_deformed=0.7):
        self.k_neighbors = k_neighbors
        self.k_eigen = k_eigen
        self.threshold_normal = threshold_normal
        self.threshold_deformed = threshold_deformed
        self.reference_fp = None
    
    def fit_reference(self, points):
        """Learn spectral fingerprint of normal part."""
        lap = build_knn_graph_laplacian(points, k=self.k_neighbors)
        self.reference_fp = extract_fingerprint(lap, self.k_eigen)
        return self.reference_fp is not None
    
    def detect(self, points):
        """Compare test part against reference. Returns dict with score and verdict."""
        if self.reference_fp is None:
            raise ValueError("Reference not fitted. Call fit_reference() first.")
        
        lap = build_knn_graph_laplacian(points, k=self.k_neighbors)
        test_fp = extract_fingerprint(lap, self.k_eigen)
        
        if test_fp is None:
            return {"score": 1.0, "verdict": "ANOMALOUS", "details": "Failed to extract fingerprint"}
        
        score = spectral_distance(self.reference_fp, test_fp)
        
        if score < self.threshold_normal:
            verdict = "NORMAL"
        elif score < self.threshold_deformed:
            verdict = "DEFORMED"
        else:
            verdict = "ANOMALOUS"
        
        return {
            "score": score,
            "verdict": verdict,
            "reference_density": self.reference_fp["density"],
            "test_density": test_fp["density"]
        }
    
    def batch_detect(self, scan_list):
        """Detect anomalies in multiple scans. Returns list of results."""
        return [self.detect(points) for points in scan_list]
