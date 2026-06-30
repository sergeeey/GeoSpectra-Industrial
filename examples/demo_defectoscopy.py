"""
Demo: Defectoscopy on synthetic 3D geometries.

Simulates industrial scenario:
1. Normal part: perfect sphere point cloud
2. Test parts: sphere with various deformations
3. Detect anomalies via spectral fingerprinting
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from core.anomaly_detector import SpectralAnomalyDetector


def generate_sphere(n_points=500, radius=1.0, noise=0.0, seed=42):
    """Generate 3D sphere point cloud with optional noise."""
    rng = np.random.default_rng(seed)
    pts = rng.standard_normal((n_points, 3))
    pts = pts / np.linalg.norm(pts, axis=1, keepdims=True) * radius
    if noise > 0:
        pts += rng.normal(0, noise, pts.shape)
    return pts


def generate_deformed_sphere(n_points=500, radius=1.0, deformation=0.1, seed=42):
    """Generate sphere with localized deformation (simulates dent/bulge)."""
    rng = np.random.default_rng(seed)
    pts = rng.standard_normal((n_points, 3))
    pts = pts / np.linalg.norm(pts, axis=1, keepdims=True) * radius
    # Add localized deformation on one side
    mask = pts[:, 0] > 0.5
    pts[mask, 0] += deformation * radius
    return pts


def main():
    print("="*60)
    print("GEOSPECTRA INDUSTRIAL — Defectoscopy Demo")
    print("="*60)
    
    # 1. Reference: normal sphere
    print("\n[1] Reference part: normal sphere")
    ref_points = generate_sphere(n_points=500, radius=1.0, noise=0.01)
    
    detector = SpectralAnomalyDetector(k_neighbors=12, k_eigen=15)
    success = detector.fit_reference(ref_points)
    print(f"    Reference fingerprint extracted: {success}")
    
    # 2. Test parts
    test_cases = [
        ("Normal sphere (low noise)", generate_sphere(n_points=500, radius=1.0, noise=0.02, seed=43)),
        ("Normal sphere (medium noise)", generate_sphere(n_points=500, radius=1.0, noise=0.05, seed=44)),
        ("Slightly deformed (dent)", generate_deformed_sphere(n_points=500, radius=1.0, deformation=0.05, seed=45)),
        ("Strongly deformed (dent)", generate_deformed_sphere(n_points=500, radius=1.0, deformation=0.15, seed=46)),
        ("Wrong radius (0.8)", generate_sphere(n_points=500, radius=0.8, seed=47)),
        ("Wrong radius (1.3)", generate_sphere(n_points=500, radius=1.3, seed=48)),
    ]
    
    print("\n[2] Testing parts:")
    results = []
    for name, points in test_cases:
        result = detector.detect(points)
        results.append((name, result))
        sym = {"NORMAL": "G", "DEFORMED": "Y", "ANOMALOUS": "R"}[result["verdict"]]
        print(f"    [{sym}] {name:30s}: score={result['score']:.3f} → {result['verdict']}")
    
    # 3. Summary
    print("\n[3] Summary:")
    normal = sum(1 for _, r in results if r["verdict"] == "NORMAL")
    deformed = sum(1 for _, r in results if r["verdict"] == "DEFORMED")
    anomalous = sum(1 for _, r in results if r["verdict"] == "ANOMALOUS")
    print(f"    NORMAL: {normal}, DEFORMED: {deformed}, ANOMALOUS: {anomalous}")
    
    accuracy = normal >= 2 and deformed >= 1 and anomalous >= 2
    print(f"\n    Detection accuracy acceptable: {accuracy}")
    print(f"    Status: {'DEMO PASSED' if accuracy else 'NEEDS TUNING'}")
    
    print("\n" + "="*60)
    print("Next steps:")
    print("  1. Load real 3D scan (STL, PLY, OBJ)")
    print("  2. Set appropriate thresholds for your industry")
    print("  3. Integrate with CT/3D scanning pipeline")
    print("="*60)


if __name__ == "__main__":
    main()
