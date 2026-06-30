"""Demo: Medical implant conformity check.

Usage: python examples/demo_implant_inspection.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from core.anomaly_detector import SpectralAnomalyDetector


def generate_hip_implant(n=1000, r_head=0.14, l_stem=0.12, noise=0.0):
    """Generate simplified hip implant point cloud."""
    # Femoral head (sphere)
    n_head = int(n * 0.3)
    phi = np.random.uniform(0, np.pi, n_head)
    theta = np.random.uniform(0, 2*np.pi, n_head)
    head = np.column_stack([
        r_head * np.sin(phi) * np.cos(theta),
        r_head * np.sin(phi) * np.sin(theta),
        r_head * np.cos(phi),
    ])
    
    # Stem (cylinder)
    n_stem = n - n_head
    z = np.random.uniform(-l_stem, 0, n_stem)
    theta = np.random.uniform(0, 2*np.pi, n_stem)
    r = 0.03
    stem = np.column_stack([
        r * np.cos(theta),
        r * np.sin(theta),
        z,
    ])
    
    implant = np.vstack([head, stem])
    if noise > 0:
        implant += np.random.normal(0, noise, implant.shape)
    return implant


def main():
    print("=" * 50)
    print("MEDICAL IMPLANT INSPECTION")
    print("=" * 50)
    
    ref = generate_hip_implant(n=1000, noise=0.001)
    detector = SpectralAnomalyDetector()
    detector.fit_reference(ref)
    
    tests = [
        ("Good implant", generate_hip_implant(1000, noise=0.002)),
        ("Oversized head", generate_hip_implant(1000, r_head=0.16, noise=0.001)),
        ("Short stem", generate_hip_implant(1000, l_stem=0.08, noise=0.001)),
        ("Noisy scan", generate_hip_implant(1000, noise=0.02)),
    ]
    
    for name, scan in tests:
        result = detector.detect(scan)
        print(f"{name:15s}: {result['verdict']:12s} (score={result['distance']:.3f})")


if __name__ == "__main__":
    main()
