"""Unit tests for GeoSpectra-Industrial core functionality.

Run: python -m pytest tests/test_core.py -v
"""

import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.spectral_fingerprint import extract_fingerprint, feature_vector
from core.anomaly_detector import SpectralAnomalyDetector
from core.patch_fingerprint import fps_sampling, extract_patch, build_patch_bank
from core.patch_bank_detector import PatchBankDetector


class TestFingerprint:
    def test_extract_not_none(self):
        points = np.random.randn(100, 3)
        fp = extract_fingerprint(points)
        assert fp is not None
    
    def test_has_spectral_and_geometric(self):
        points = np.random.randn(100, 3)
        fp = extract_fingerprint(points)
        assert "spectral" in fp
        assert "geometric" in fp
    
    def test_spectral_has_required_keys(self):
        points = np.random.randn(100, 3)
        fp = extract_fingerprint(points)
        spec = fp["spectral"]
        assert "density" in spec
        assert "r" in spec
        assert "cv" in spec
        assert len(spec["density"]) == 15
    
    def test_geometric_has_required_keys(self):
        points = np.random.randn(100, 3)
        fp = extract_fingerprint(points)
        geo = fp["geometric"]
        for key in ["pca_ratio_21", "pca_ratio_32", "pca_ratio_31",
                     "bbox_ratio_21", "bbox_ratio_32", "centroid_rms", "asymmetry"]:
            assert key in geo
    
    def test_feature_vector_length(self):
        points = np.random.randn(100, 3)
        fp = extract_fingerprint(points)
        vec = feature_vector(fp)
        # 15 density bins + r + cv + 7 geometric = 25
        assert len(vec) == 25
    
    def test_scale_invariance(self):
        np.random.seed(42)
        points = np.random.randn(100, 3)
        fp1 = extract_fingerprint(points)
        fp2 = extract_fingerprint(points * 2.0)
        
        vec1 = feature_vector(fp1)
        vec2 = feature_vector(fp2)
        
        # Spectral features should be scale-invariant (median normalized)
        np.testing.assert_allclose(
            fp1["spectral"]["density"], fp2["spectral"]["density"], rtol=0.1
        )


class TestAnomalyDetector:
    def test_single_reference_mode(self):
        np.random.seed(42)
        ref = np.random.randn(200, 3)
        detector = SpectralAnomalyDetector()
        detector.fit_reference(ref)
        
        # Same points should be NORMAL
        result = detector.detect(ref)
        assert result["verdict"] == "NORMAL"
    
    def test_detects_heavy_noise(self):
        np.random.seed(42)
        ref = np.random.randn(200, 3)
        detector = SpectralAnomalyDetector()
        detector.fit_reference(ref)
        
        # Heavy noise should be ANOMALOUS
        noisy = ref + np.random.normal(0, 0.5, ref.shape)
        result = detector.detect(noisy)
        assert result["verdict"] in ("DEFORMED", "ANOMALOUS")
    
    def test_detects_hole(self):
        np.random.seed(42)
        # Create sphere
        ref = np.random.randn(200, 3)
        ref = ref / np.linalg.norm(ref, axis=1, keepdims=True)
        
        detector = SpectralAnomalyDetector()
        detector.fit_reference(ref)
        
        # Remove a chunk (simulated hole)
        mask = ref[:, 2] > -0.3
        damaged = ref[mask]
        
        result = detector.detect(damaged)
        assert result["verdict"] in ("DEFORMED", "ANOMALOUS")
    
    def test_save_load(self):
        np.random.seed(42)
        ref = np.random.randn(100, 3)
        detector = SpectralAnomalyDetector()
        detector.fit_reference(ref)
        
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name
        
        detector.save(path)
        loaded = SpectralAnomalyDetector.load(path)
        
        result1 = detector.detect(ref)
        result2 = loaded.detect(ref)
        assert result1["verdict"] == result2["verdict"]
        
        import os
        os.unlink(path)


class TestPatchBankDetector:
    def test_mode_a_pose_invariance(self):
        """Mode A should not produce false positives on rotated clean scans."""
        np.random.seed(42)
        # Box shape (more geometric diversity than sphere)
        pts = np.random.uniform(-1, 1, (500, 3))
        
        det = PatchBankDetector(n_patches=16, patch_size=32, top_k_ratio=0.15)
        det.fit(pts)
        
        # Rotate 45 degrees
        angle = np.radians(45)
        R = np.array([[np.cos(angle), -np.sin(angle), 0],
                      [np.sin(angle), np.cos(angle), 0],
                      [0, 0, 1]])
        rotated = pts @ R.T
        
        result = det.detect(rotated)
        assert result["verdict"] == "NORMAL", f"Expected NORMAL, got {result['verdict']}"
    
    def test_mode_a_detects_defects(self):
        """Mode A should detect scans with defects."""
        np.random.seed(42)
        pts = np.random.uniform(-1, 1, (500, 3))
        
        det = PatchBankDetector(n_patches=16, patch_size=32, top_k_ratio=0.15)
        det.fit(pts)
        
        # Add bulge
        defective = pts.copy()
        center = pts[0]
        dists = np.linalg.norm(pts - center, axis=1)
        mask = dists < np.percentile(dists, 30)
        dirs = pts[mask] - center
        norms = np.linalg.norm(dirs, axis=1, keepdims=True)
        norms[norms == 0] = 1
        defective[mask] += 0.15 * (dirs / norms)
        
        result = det.detect(defective)
        assert result["verdict"] in ("DEFORMED", "ANOMALOUS"), \
            f"Expected defect detected, got {result['verdict']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
