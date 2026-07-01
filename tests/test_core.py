"""Unit tests for GeoSpectra-Industrial core modules."""

import numpy as np
import pytest

from core.spectral_fingerprint import extract_fingerprint, feature_vector
from core.anomaly_detector import SpectralAnomalyDetector
from core.patch_fingerprint import fps_sampling, extract_patch, build_patch_bank
from core.patch_bank_detector import PatchBankDetector
from core.two_mode_detector import TwoModeDetector


def make_sphere(n=512):
    """Generate a small sphere point cloud."""
    indices = np.arange(n, dtype=float) + 0.5
    phi = np.arccos(1 - 2 * indices / n)
    theta = np.pi * (1 + 5**0.5) * indices
    x = np.sin(phi) * np.cos(theta)
    y = np.sin(phi) * np.sin(theta)
    z = np.cos(phi)
    return np.column_stack([x, y, z])


class TestFingerprint:
    def test_extract_not_none(self):
        pts = make_sphere(256)
        fp = extract_fingerprint(pts, k=8, k_eigen=8)
        assert fp is not None

    def test_has_spectral_and_geometric(self):
        pts = make_sphere(256)
        fp = extract_fingerprint(pts, k=8, k_eigen=8)
        assert "spectral" in fp
        assert "geometric" in fp

    def test_spectral_has_required_keys(self):
        pts = make_sphere(256)
        fp = extract_fingerprint(pts, k=8, k_eigen=8)
        spec = fp["spectral"]
        assert "density" in spec
        assert "r" in spec
        assert "cv" in spec

    def test_geometric_has_required_keys(self):
        pts = make_sphere(256)
        fp = extract_fingerprint(pts, k=8, k_eigen=8)
        geo = fp["geometric"]
        assert "pca_ratio_21" in geo
        assert "pca_ratio_32" in geo

    def test_feature_vector_length(self):
        pts = make_sphere(256)
        fp = extract_fingerprint(pts, k=8, k_eigen=8)
        vec = feature_vector(fp)
        assert len(vec) == 25  # 15 density bins + r + cv + 7 geometric

    def test_scale_invariance(self):
        pts = make_sphere(256)
        fp1 = extract_fingerprint(pts, k=8, k_eigen=8)
        fp2 = extract_fingerprint(pts * 2.0, k=8, k_eigen=8)
        assert fp1 is not None and fp2 is not None
        np.testing.assert_allclose(fp1["spectral"]["density"], fp2["spectral"]["density"], rtol=0.1)


class TestAnomalyDetector:
    def test_single_reference_mode(self):
        pts = make_sphere(256)
        det = SpectralAnomalyDetector(k=8, k_eigen=8)
        det.fit_reference(pts)
        result = det.detect(pts)
        assert result["verdict"] == "NORMAL"

    def test_detects_heavy_noise(self):
        pts = make_sphere(256)
        det = SpectralAnomalyDetector(k=8, k_eigen=8)
        det.fit_reference(pts)
        noisy = pts + np.random.normal(0, 0.1, pts.shape)
        result = det.detect(noisy)
        assert result["verdict"] in ("DEFORMED", "ANOMALOUS")

    def test_detects_hole(self):
        pts = make_sphere(256)
        det = SpectralAnomalyDetector(k=8, k_eigen=8)
        det.fit_reference(pts)
        # Remove 20% of points
        idx = np.random.choice(len(pts), int(len(pts) * 0.8), replace=False)
        incomplete = pts[idx]
        result = det.detect(incomplete)
        assert result["verdict"] in ("DEFORMED", "ANOMALOUS")

    def test_save_load(self):
        pts = make_sphere(256)
        det = SpectralAnomalyDetector(k=8, k_eigen=8)
        det.fit_reference(pts)
        det.save("/tmp/test_detector.json")
        det2 = SpectralAnomalyDetector.load("/tmp/test_detector.json")
        result = det2.detect(pts)
        assert result["verdict"] == "NORMAL"


class TestPatchBankDetector:
    def test_fit_and_detect_clean(self):
        pts = make_sphere(256)
        det = PatchBankDetector(n_patches=16, patch_size=32)
        det.fit(pts)
        result = det.detect(pts)
        assert result["verdict"] == "NORMAL"

    def test_detects_defect(self):
        pts = make_sphere(256)
        det = PatchBankDetector(n_patches=16, patch_size=32)
        det.fit(pts)
        # Add bulge
        defective = pts.copy()
        defective[:50] += 0.2
        result = det.detect(defective)
        assert result["verdict"] in ("DEFORMED", "ANOMALOUS")


class TestTwoModeDetector:
    def test_mode_a_detects(self):
        pts = make_sphere(256)
        det = TwoModeDetector(mode="A", n_patches=16, patch_size=32)
        det.fit(pts)
        result = det.detect(pts)
        assert result["verdict"] == "NORMAL"

    def test_mode_b_detects(self):
        pts = make_sphere(256)
        det = TwoModeDetector(mode="B", n_patches=16, patch_size=32)
        det.fit(pts)
        result = det.detect(pts)
        assert result["verdict"] in ("NORMAL", "UNRELIABLE_ALIGNMENT")

    def test_auto_mode_runs(self):
        pts = make_sphere(256)
        det = TwoModeDetector(mode="auto", n_patches=16, patch_size=32)
        det.fit(pts)
        result = det.detect(pts)
        assert "verdict" in result
        assert "mode_used" in result
