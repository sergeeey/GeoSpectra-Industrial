"""TwoModeDetector — unified anomaly detection with Mode A / Mode B selection.

ADR-IND-018: Two-Mode Architecture.

  Mode A (PatchBankDetector): Registration-free, pose-invariant, fast.
    - Use when: scan pose unknown, speed critical, coarse screening
    - 0% FP on rotation/translation, ~0.27s/scan
    - LIMITATION: no localization, fails on jitter/occlusion

  Mode B (PatchAnomalyDetector): ICP-aligned, precise localization.
    - Use when: scan roughly aligned, metrology-grade inspection needed
    - Exact defect position, ~2.5s/scan
    - LIMITATION: requires successful registration (23% FP if fails)

Modes are NOT sequential — they are alternative strategies.
The operator selects mode based on use case, OR uses "auto" escalation.

AUTO escalation policy (ADR-IND-019):
  1. Run Mode A (fast screening)
  2. If Mode A reports ANOMALOUS with high confidence AND operator wants
     localization → run Mode B on the same scan
  3. If registration fails in Mode B → fall back to Mode A result
  4. Report BOTH results with mode labels
"""

import json
import time
import numpy as np

from core.patch_bank_detector import PatchBankDetector
from core.patch_detector import PatchAnomalyDetector


class TwoModeDetector:
    """Unified detector supporting Mode A, Mode B, or auto escalation.
    
    Usage:
        detector = TwoModeDetector(mode="A")  # or "B" or "auto"
        detector.fit(reference_points)
        result = detector.detect(scan_points)  # unified result format
    
    The result always contains:
      - verdict: NORMAL / DEFORMED / ANOMALOUS / LOCAL_DEFECT / etc.
      - confidence: 0-1
      - mode_used: "A" / "B" / "both"
      - mode_a_result: full Mode A result (if run)
      - mode_b_result: full Mode B result (if run)
      - runtime_ms: total detection time
    """
    
    def __init__(self, mode="auto",
                 n_patches=64, patch_size=128, top_k_ratio=0.05,
                 patch_threshold=2.0,
                 global_deformed_threshold=1.5,
                 global_anomalous_threshold=4.0,
                 registration_confidence_threshold=0.5,
                 mode_a_threshold_anomalous=4.0,
                 mode_a_threshold_deformed=1.5,
                 auto_escalate_confidence=0.8):
        if mode not in ("A", "B", "auto"):
            raise ValueError(f"mode must be 'A', 'B', or 'auto', got {mode}")
        
        self.mode = mode
        self.auto_escalate_confidence = auto_escalate_confidence
        
        self.mode_a = PatchBankDetector(
            n_patches=n_patches, patch_size=patch_size, top_k_ratio=top_k_ratio,
            threshold_deformed=mode_a_threshold_deformed,
            threshold_anomalous=mode_a_threshold_anomalous,
        )
        self.mode_b = PatchAnomalyDetector(
            n_patches=n_patches, patch_size=patch_size, top_k_ratio=top_k_ratio,
            patch_threshold=patch_threshold,
            global_deformed_threshold=global_deformed_threshold,
            global_anomalous_threshold=global_anomalous_threshold,
            registration_confidence_threshold=registration_confidence_threshold,
        )
        self._fitted = False
    
    def fit(self, reference_points):
        self.mode_a.fit(reference_points)
        self.mode_b.fit(reference_points)
        self._fitted = True
        return self
    
    def detect(self, scan_points):
        if not self._fitted:
            raise RuntimeError("Not fitted. Call fit() first.")
        
        t0 = time.perf_counter()
        
        if self.mode == "A":
            result = self._detect_mode_a_only(scan_points)
        elif self.mode == "B":
            result = self._detect_mode_b_only(scan_points)
        else:
            result = self._detect_auto(scan_points)
        
        result["runtime_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        result["mode_selected"] = self.mode
        return result
    
    def _detect_mode_a_only(self, scan_points):
        a_result = self.mode_a.detect(scan_points)
        return {
            "verdict": self._unify_verdict_a(a_result["verdict"]),
            "confidence": a_result["confidence"],
            "anomaly_score": a_result["anomaly_score"],
            "mode_used": "A",
            "mode_a_result": a_result,
            "mode_b_result": None,
            "escalated": False,
            "escalation_reason": None,
        }
    
    def _detect_mode_b_only(self, scan_points):
        b_result = self.mode_b.detect(scan_points, use_patches=True)
        return {
            "verdict": b_result["verdict"],
            "confidence": b_result["confidence"],
            "anomaly_score": b_result.get("combined_score", 0.0),
            "mode_used": "B",
            "mode_a_result": None,
            "mode_b_result": b_result,
            "escalated": False,
            "escalation_reason": None,
        }
    
    def _detect_auto(self, scan_points):
        a_result = self.mode_a.detect(scan_points)
        
        should_escalate = (
            a_result["verdict"] in ("ANOMALOUS", "DEFORMED") and
            a_result["confidence"] >= self.auto_escalate_confidence
        )
        
        if not should_escalate:
            return {
                "verdict": self._unify_verdict_a(a_result["verdict"]),
                "confidence": a_result["confidence"],
                "anomaly_score": a_result["anomaly_score"],
                "mode_used": "A",
                "mode_a_result": a_result,
                "mode_b_result": None,
                "escalated": False,
                "escalation_reason": (
                    "mode_a_normal" if a_result["verdict"] == "NORMAL"
                    else "mode_a_low_confidence"
                ),
            }
        
        b_result = self.mode_b.detect(scan_points, use_patches=True)
        b_usable = (
            b_result["verdict"] != "UNRELIABLE_ALIGNMENT" and
            "reason" not in b_result
        )
        
        if b_usable:
            return {
                "verdict": b_result["verdict"],
                "confidence": b_result["confidence"],
                "anomaly_score": b_result.get("combined_score", 0.0),
                "mode_used": "B",
                "mode_a_result": a_result,
                "mode_b_result": b_result,
                "escalated": True,
                "escalation_reason": "mode_a_high_confidence_anomaly",
            }
        else:
            return {
                "verdict": self._unify_verdict_a(a_result["verdict"]),
                "confidence": a_result["confidence"] * 0.8,
                "anomaly_score": a_result["anomaly_score"],
                "mode_used": "A (B failed)",
                "mode_a_result": a_result,
                "mode_b_result": b_result,
                "escalated": True,
                "escalation_reason": f"mode_b_failed: {b_result.get('reason', 'unreliable_alignment')}",
            }
    
    def _unify_verdict_a(self, verdict_a):
        mapping = {"NORMAL": "NORMAL", "DEFORMED": "DEFORMED",
                   "ANOMALOUS": "ANOMALOUS", "BAD_SCAN": "BAD_SCAN"}
        return mapping.get(verdict_a, verdict_a)
    
    def save(self, path_prefix):
        if not self._fitted:
            raise RuntimeError("Not fitted")
        self.mode_a.save(f"{path_prefix}_mode_a.json")
        self.mode_b.save(f"{path_prefix}_mode_b.json")
        config = {
            "mode": self.mode,
            "auto_escalate_confidence": self.auto_escalate_confidence,
            "mode_a_path": f"{path_prefix}_mode_a.json",
            "mode_b_path": f"{path_prefix}_mode_b.json",
        }
        with open(f"{path_prefix}_config.json", 'w') as f:
            json.dump(config, f, indent=2)
    
    @classmethod
    def load(cls, path_prefix):
        with open(f"{path_prefix}_config.json") as f:
            config = json.load(f)
        det = cls.__new__(cls)
        det.mode = config["mode"]
        det.auto_escalate_confidence = config["auto_escalate_confidence"]
        det.mode_a = PatchBankDetector.load(config["mode_a_path"])
        det.mode_b = PatchAnomalyDetector.load(config["mode_b_path"])
        det._fitted = True
        return det
