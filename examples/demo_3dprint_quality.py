"""Demo: 3D print quality control with spectral fingerprinting.

Usage: python examples/demo_3dprint_quality.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from core.anomaly_detector import SpectralAnomalyDetector


def generate_cube(n=1000, size=1.0, noise=0.0):
    """Generate a cube point cloud with surface points only."""
    pts = np.random.uniform(-size/2, size/2, (n * 3, 3))
    eps = size * 0.05
    on_surface = (
        (np.abs(pts[:, 0]) > size/2 - eps) |
        (np.abs(pts[:, 1]) > size/2 - eps) |
        (np.abs(pts[:, 2]) > size/2 - eps)
    )
    pts = pts[on_surface][:n]
    if len(pts) < n:
        pts = np.vstack([pts, np.random.uniform(-size/2, size/2, (n - len(pts), 3))])
    if noise > 0:
        pts += np.random.normal(0, noise, pts.shape)
    return pts[:n]


def main():
    print("=" * 50)
    print("3D PRINT QUALITY CONTROL")
    print("=" * 50)
    
    # Reference: ideal cube
    ref = generate_cube(n=1000, size=1.0, noise=0.01)
    detector = SpectralAnomalyDetector()
    detector.fit_reference(ref)
    
    # Test prints
    tests = [
        ("Good print", generate_cube(1000, 1.0, 0.02)),
        ("Noisy print", generate_cube(1000, 1.0, 0.08)),
        ("Wrong scale", generate_cube(1000, 1.15, 0.02)),
        ("Layer shift", generate_cube(1000, 1.0, 0.02) + [0.1, 0, 0]),
    ]
    
    for name, scan in tests:
        result = detector.detect(scan)
        print(f"{name:15s}: {result['verdict']:12s} (score={result['distance']:.3f})")


if __name__ == "__main__":
    main()
