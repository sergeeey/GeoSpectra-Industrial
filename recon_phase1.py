"""Phase 1 Recon — spectral fingerprinting proof of concept."""

import numpy as np
from core.spectral_fingerprint import extract_fingerprint, feature_vector
from core.anomaly_detector import SpectralAnomalyDetector


def make_sphere(n=2048):
    """Fibonacci sphere."""
    indices = np.arange(n, dtype=float) + 0.5
    phi = np.arccos(1 - 2 * indices / n)
    theta = np.pi * (1 + 5**0.5) * indices
    x = np.sin(phi) * np.cos(theta)
    y = np.sin(phi) * np.sin(theta)
    z = np.cos(phi)
    return np.column_stack([x, y, z])


def main():
    print("Phase 1 Recon: Spectral Fingerprinting")
    print("=" * 50)
    
    ref = make_sphere(2048)
    
    det = SpectralAnomalyDetector()
    det.fit_reference(ref)
    
    # Test clean
    result = det.detect(ref)
    print(f"Clean: {result['verdict']} (dist={result['distance']:.3f})")
    
    # Test noisy
    noisy = ref + np.random.normal(0, 0.02, ref.shape)
    result = det.detect(noisy)
    print(f"Noisy: {result['verdict']} (dist={result['distance']:.3f})")
    
    # Test bulge
    bulge = ref.copy()
    center = bulge[0]
    dists = np.linalg.norm(bulge - center, axis=1)
    mask = dists < 0.3
    bulge[mask] += 0.05
    result = det.detect(bulge)
    print(f"Bulge: {result['verdict']} (dist={result['distance']:.3f})")


if __name__ == "__main__":
    main()
