"""Fast benchmark — core metrics in <30 seconds."""

import time
import numpy as np
from core.spectral_fingerprint import extract_fingerprint
from core.anomaly_detector import SpectralAnomalyDetector


def make_sphere(n=512):
    indices = np.arange(n, dtype=float) + 0.5
    phi = np.arccos(1 - 2 * indices / n)
    theta = np.pi * (1 + 5**0.5) * indices
    x = np.sin(phi) * np.cos(theta)
    y = np.sin(phi) * np.sin(theta)
    z = np.cos(phi)
    return np.column_stack([x, y, z])


def main():
    print("Fast Benchmark")
    print("=" * 40)
    
    ref = make_sphere(512)
    det = SpectralAnomalyDetector(k=8, k_eigen=8)
    det.fit_reference(ref)
    
    # Speed
    t0 = time.perf_counter()
    for _ in range(10):
        det.detect(ref)
    elapsed = (time.perf_counter() - t0) / 10 * 1000
    
    print(f"Speed: {elapsed:.1f} ms/scan")
    print(f"Clean detection: {det.detect(ref)['verdict']}")
    
    noisy = ref + np.random.normal(0, 0.05, ref.shape)
    print(f"Noisy detection: {det.detect(noisy)['verdict']}")


if __name__ == "__main__":
    main()
