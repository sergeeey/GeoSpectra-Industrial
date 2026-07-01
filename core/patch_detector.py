"""PatchAnomalyDetector v2 — hierarchical anomaly detection with registration gate.

ADR-IND-009: Hierarchical detector: global + patch + rule-based decision.
ADR-IND-011: Rule-based override — patch high → LOCAL_DEFECT regardless of global.
ADR-IND-013: Registration gate — patch layer only runs after successful ICP alignment.

Architecture:
  Pre-step: ICP registration (if patches enabled)
  Global Layer: whole-object spectral + geometric fingerprint (always runs)
  Patch Layer:  local patch fingerprints, deterministic centers (post-registration)
  Decision Layer: rule-based
    - if registration_failed → UNRELIABLE_ALIGNMENT
    - elif patch_score >= patch_threshold → LOCAL_DEFECT
    - elif global_score >= global_threshold → GLOBAL_DEFORMED
    - else → NORMAL

Without registration gate: 100% false positives on rotated/translated scans (ADR-IND-012).
"""

import json
import numpy as np
from scipy.spatial.distance import cdist

from core import SpectralAnomalyDetector
from core.spectral_fingerprint import extract_fingerprint
from core.patch_fingerprint import build_patch_bank, extract_patch, patch_feature_vector


class PatchAnomalyDetector:
    """Hierarchical anomaly detector with rule-based decision override."""
    
    VERDICTS = ["NORMAL", "NOISY", "GLOBAL_DEFORMED", "LOCAL_DEFECT", "BAD_SCAN", "LOW_COHERENCE", "UNRELIABLE_ALIGNMENT"]
    
    def __init__(self, n_patches=64, patch_size=128, top_k_ratio=0.05,
                 global_weight=0.2, patch_weight=0.8,
                 k=12, k_eigen=15,
                 patch_threshold=2.0,
                 global_deformed_threshold=1.5,
                 global_anomalous_threshold=4.0,
                 registration_confidence_threshold=0.3):
        self.n_patches = n_patches
        self.patch_size = patch_size
        self.top_k = max(1, int(n_patches * top_k_ratio))
        self.global_weight = global_weight
        self.patch_weight = patch_weight
        self.k = k
        self.k_eigen = k_eigen
        
        # ADR-IND-011: separate thresholds for rule-based decision
        self.patch_threshold = patch_threshold
        self.global_deformed_threshold = global_deformed_threshold
        self.global_anomalous_threshold = global_anomalous_threshold
        
        # ADR-IND-013: registration gate
        self.registration_confidence_threshold = registration_confidence_threshold
        
        self.global_detector = SpectralAnomalyDetector(k=k, k_eigen=k_eigen)
        self.ref_patch_bank = None
        self.ref_points = None
        self._fitted = False
    
    def fit(self, reference_points):
        """Fit on golden reference."""
        self.ref_points = reference_points.copy()
        
        self.global_detector.fit_reference(
            reference_points,
            threshold_deformed=self.global_deformed_threshold,
            threshold_anomalous=self.global_anomalous_threshold,
        )
        
        self.ref_patch_bank = build_patch_bank(
            reference_points,
            n_patches=self.n_patches,
            patch_size=self.patch_size,
        )
        
        self._fitted = True
        return self
    
    def detect(self, scan_points, use_patches=True):
        """Detect anomalies with registration gate + rule-based override.
        
        Pipeline (ADR-IND-013):
        1. If use_patches: register scan → reference
        2. If registration FAIL → UNRELIABLE_ALIGNMENT (no patch scores)
        3. Else: run patch layer on aligned scan
        4. Global layer always runs (on original scan)
        5. Decision: rule-based (ADR-IND-011)
        
        Decision logic:
        - registration failed → UNRELIABLE_ALIGNMENT
        - patch_score >= threshold → LOCAL_DEFECT  
        - global_score >= anomalous_threshold → GLOBAL_DEFORMED
        - global_score >= deformed_threshold → GLOBAL_DEFORMED
        - else → NORMAL
        """
        if not self._fitted:
            raise RuntimeError("Not fitted. Call fit() first.")
        
        # Global score (always runs, on original scan)
        global_result = self.global_detector.detect(scan_points)
        global_score = global_result["distance"]
        
        # Registration gate (ADR-IND-013)
        reg_report = None
        patch_score = 0.0
        n_anomalous = 0
        top_patches = []
        heatmap = []
        
        if use_patches and self.ref_patch_bank is not None:
            from core.registration import align_scan_to_reference, registration_quality
            
            try:
                aligned_scan, reg_report, _, _ = align_scan_to_reference(
                    self.ref_points, scan_points, use_icp=True
                )
                
                # Registration gate: if confidence too low, skip patches
                if reg_report["confidence"] < self.registration_confidence_threshold:
                    return self._make_result(
                        verdict="UNRELIABLE_ALIGNMENT",
                        confidence=1.0 - reg_report["confidence"],
                        global_score=global_score,
                        patch_score=0.0,
                        reg_report=reg_report,
                    )
                
                # Run patch layer on ALIGNED scan
                patch_result = self._run_patch_layer(aligned_scan)
                patch_score = patch_result["patch_score"]
                n_anomalous = patch_result["n_anomalous"]
                top_patches = patch_result["top_patches"]
                heatmap = patch_result["heatmap"]
                
            except Exception as e:
                return self._make_result(
                    verdict="UNRELIABLE_ALIGNMENT",
                    confidence=0.0,
                    global_score=global_score,
                    patch_score=0.0,
                    reason=f"registration_error: {str(e)}",
                )
        
        # ADR-IND-016: Coherence Check
        # If patch_score is high but global_score is low, the signals are
        # incoherent — likely a sampling artifact or registration residual,
        # not a real local defect.
        coherence_threshold = 3.0  # patch_score / global_score ratio
        if global_score > 0.5:
            coherence_ratio = patch_score / global_score
        else:
            coherence_ratio = float('inf') if patch_score > 0 else 0.0
        is_coherent = coherence_ratio < coherence_threshold or global_score >= self.global_deformed_threshold
        
        # RULE-BASED DECISION (ADR-IND-011) + coherence gate
        if reg_report and reg_report.get("status") == "FAIL":
            verdict = "UNRELIABLE_ALIGNMENT"
            confidence = 0.5
        elif patch_score >= self.patch_threshold and not is_coherent:
            verdict = "LOW_COHERENCE"
            confidence = min(1.0, patch_score / 6.0)
        elif patch_score >= self.patch_threshold and is_coherent:
            verdict = "LOCAL_DEFECT"
            confidence = min(1.0, patch_score / 6.0 + 0.5)
        elif global_score >= self.global_anomalous_threshold:
            verdict = "GLOBAL_DEFORMED"
            confidence = min(1.0, global_score / 8.0 + 0.5)
        elif global_score >= self.global_deformed_threshold:
            verdict = "GLOBAL_DEFORMED"
            confidence = min(1.0, global_score / 4.0 + 0.5)
        elif global_score >= 0.5:
            verdict = "NOISY"
            confidence = min(1.0, global_score / 2.0)
        else:
            verdict = "NORMAL"
            confidence = min(1.0, 1.0 - global_score / 2.0)
        
        combined_score = max(global_score, patch_score)
        
        return {
            "verdict": verdict,
            "confidence": round(confidence, 3),
            "global_score": round(global_score, 3),
            "patch_score": round(patch_score, 3),
            "combined_score": round(combined_score, 3),
            "n_anomalous_patches": n_anomalous,
            "top_patches": top_patches,
            "heatmap": heatmap,
            "registration": reg_report,
            "thresholds": {
                "patch_local_defect": self.patch_threshold,
                "global_deformed": self.global_deformed_threshold,
                "global_anomalous": self.global_anomalous_threshold,
                "registration_min": self.registration_confidence_threshold,
            },
        }
    
    def _run_patch_layer(self, aligned_scan):
        """Run patch fingerprint comparison on aligned scan."""
        from core.patch_fingerprint import extract_patch, patch_feature_vector
        
        ref_centers = [p["center"] for p in self.ref_patch_bank["patches"]]
        scan_patches = []
        scan_features = []
        
        for ref_center_idx in ref_centers:
            ref_pos = self.ref_points[ref_center_idx]
            scan_dists = np.linalg.norm(aligned_scan - ref_pos, axis=1)
            scan_center = np.argmin(scan_dists)
            patch_pts, _ = extract_patch(aligned_scan, scan_center, self.patch_size)
            if len(patch_pts) >= 10:
                fp = extract_fingerprint(patch_pts, k=8, k_eigen=8)
                if fp:
                    scan_patches.append({"center": scan_center, "fingerprint": fp})
                    scan_features.append(patch_feature_vector(fp))
        
        if not scan_patches:
            return {"patch_score": 0.0, "n_anomalous": 0, "top_patches": [], "heatmap": []}
        
        scan_features = np.array(scan_features)
        dist_matrix = cdist(scan_features, self.ref_patch_bank["feature_matrix"])
        patch_scores = dist_matrix.min(axis=1)
        
        top_k_scores = np.partition(patch_scores, -self.top_k)[-self.top_k:]
        patch_score = float(np.mean(top_k_scores))
        n_anomalous = int(np.sum(patch_scores > self.patch_threshold))
        
        top_indices = np.argsort(patch_scores)[-self.top_k:][::-1]
        top_patches = [{"center": scan_patches[i]["center"], "score": float(patch_scores[i])}
                       for i in top_indices]
        heatmap = [{"center": scan_patches[i]["center"], "score": float(patch_scores[i])}
                     for i in range(len(scan_patches))]
        
        return {
            "patch_score": patch_score,
            "n_anomalous": n_anomalous,
            "top_patches": top_patches,
            "heatmap": heatmap,
        }
    
    def _make_result(self, verdict, confidence, global_score, patch_score,
                     reg_report=None, reason=None):
        """Create result dict for edge cases (registration fail, error)."""
        result = {
            "verdict": verdict,
            "confidence": round(confidence, 3),
            "global_score": round(global_score, 3),
            "patch_score": round(patch_score, 3),
            "combined_score": round(max(global_score, patch_score), 3),
            "n_anomalous_patches": 0,
            "top_patches": [],
            "heatmap": [],
            "registration": reg_report,
            "thresholds": {
                "patch_local_defect": self.patch_threshold,
                "global_deformed": self.global_deformed_threshold,
                "global_anomalous": self.global_anomalous_threshold,
                "registration_min": self.registration_confidence_threshold,
            },
        }
        if reason:
            result["reason"] = reason
        return result
    
    def save(self, path):
        if not self._fitted:
            raise RuntimeError("Not fitted")
        self.global_detector.save(path.replace('.json', '_global.json'))
        data = {
            "n_patches": self.n_patches,
            "patch_size": self.patch_size,
            "top_k": self.top_k,
            "patch_threshold": self.patch_threshold,
            "global_deformed_threshold": self.global_deformed_threshold,
            "global_anomalous_threshold": self.global_anomalous_threshold,
            "ref_feature_matrix": self.ref_patch_bank["feature_matrix"].tolist(),
            "ref_patch_centers": [p["center"] for p in self.ref_patch_bank["patches"]],
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls, path):
        with open(path) as f:
            data = json.load(f)
        det = cls(
            n_patches=data["n_patches"],
            patch_size=data["patch_size"],
            top_k_ratio=data["top_k"] / data["n_patches"],
            patch_threshold=data["patch_threshold"],
            global_deformed_threshold=data["global_deformed_threshold"],
            global_anomalous_threshold=data["global_anomalous_threshold"],
        )
        det._fitted = True
        return det
