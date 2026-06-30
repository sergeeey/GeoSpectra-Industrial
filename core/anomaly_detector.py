"""
Anomaly detector for industrial defectoscopy.

Spectral fingerprint comparison → anomaly score → verdict.
"""
from .spectral_fingerprint import extract_fingerprint, fingerprint_distance, build_knn_graph_laplacian


class SpectralAnomalyDetector:
    """Detects anomalies in 3D scans by spectral fingerprint comparison."""
    
    def __init__(self, k_neighbors=12, k_eigen=15, threshold_normal=0.08, threshold_deformed=0.2):
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
        """Compare test part against reference.
        
        Returns dict: score, verdict (NORMAL/DEFORMED/ANOMALOUS)
        """
        if self.reference_fp is None:
            raise ValueError("Reference not fitted. Call fit_reference() first.")
        
        lap = build_knn_graph_laplacian(points, k=self.k_neighbors)
        test_fp = extract_fingerprint(lap, self.k_eigen)
        
        if test_fp is None:
            return {"score": 1.0, "verdict": "ANOMALOUS", "details": "Failed extraction"}
        
        score = fingerprint_distance(self.reference_fp, test_fp)
        
        if score < self.threshold_normal:
            verdict = "NORMAL"
        elif score < self.threshold_deformed:
            verdict = "DEFORMED"
        else:
            verdict = "ANOMALOUS"
        
        return {"score": score, "verdict": verdict}
    
    def calibrate(self, normal_scans):
        """Auto-calibrate thresholds from multiple normal scans."""
        scores = []
        for pts in normal_scans:
            lap = build_knn_graph_laplacian(pts, k=self.k_neighbors)
            fp = extract_fingerprint(lap, self.k_eigen)
            if fp:
                scores.append(fingerprint_distance(self.reference_fp, fp))
        if scores:
            self.threshold_normal = max(scores) * 1.5
            self.threshold_deformed = max(scores) * 3.0
        return self.threshold_normal, self.threshold_deformed
