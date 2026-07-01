"""Demo: 3D print quality control with ScanGuard."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from core.two_mode_detector import TwoModeDetector


def make_cube(n=512, size=1.0):
    """Simple cube point cloud."""
    pts = np.random.uniform(-size/2, size/2, (n, 3))
    return pts


def main():
    print("3D Print Quality Control Demo")
    print("=" * 50)
    
    ref = make_cube(512)
    det = TwoModeDetector(mode="auto")
    det.fit(ref)
    
    # Good print
    result = det.detect(ref)
    print(f"Good print: {result['verdict']}")
    
    # Warped print
    warped = ref.copy()
    warped[:, 2] *= 1.08  # Z-axis elongation
    result = det.detect(warped)
    print(f"Warped print: {result['verdict']}")
    
    # Noisy print
    noisy = ref + np.random.normal(0, 0.02, ref.shape)
    result = det.detect(noisy)
    print(f"Noisy print: {result['verdict']}")


if __name__ == "__main__":
    main()
