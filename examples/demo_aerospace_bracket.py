"""Demo: Aerospace bracket inspection with ScanGuard."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from benchmarks.industrial_mesh_suite import create_bracket
from core.two_mode_detector import TwoModeDetector


def main():
    print("Aerospace Bracket Inspection Demo")
    print("=" * 50)
    
    # Create bracket mesh
    mesh = create_bracket()
    ref_points = mesh.sample(2048)
    
    # Fit detector
    det = TwoModeDetector(mode="auto")
    det.fit(ref_points)
    print("Detector fitted on reference bracket")
    
    # Test 1: Clean scan
    result = det.detect(ref_points)
    print(f"\nClean scan: {result['verdict']} (confidence={result['confidence']})")
    
    # Test 2: Add dent
    scan = ref_points.copy()
    center_idx = np.random.randint(len(scan))
    center = scan[center_idx]
    dists = np.linalg.norm(scan - center, axis=1)
    mask = dists < np.percentile(dists, 15)
    scan[mask] -= 0.05 * (scan[mask] - center) / (dists[mask][:, None] + 1e-10)
    
    result = det.detect(scan)
    print(f"Dented scan: {result['verdict']} (confidence={result['confidence']})")
    print(f"Mode used: {result['mode_used']}")
    print(f"Runtime: {result.get('runtime_ms', 'N/A')} ms")


if __name__ == "__main__":
    main()
