"""Demo: Medical implant inspection with ScanGuard."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from core.two_mode_detector import TwoModeDetector


def make_implant(n=1024):
    """Simplified hip implant shape."""
    t = np.linspace(0, 2*np.pi, n)
    r = 0.5 + 0.1 * np.sin(3*t)
    x = r * np.cos(t)
    y = r * np.sin(t)
    z = np.linspace(-1, 1, n)
    return np.column_stack([x, y, z])


def main():
    print("Medical Implant Inspection Demo")
    print("=" * 50)
    
    ref = make_implant(1024)
    
    det = TwoModeDetector(mode="A")
    det.fit(ref)
    
    # Clean
    result = det.detect(ref)
    print(f"Clean: {result['verdict']} ({result['confidence']})")
    
    # With defect
    scan = ref.copy()
    scan[100:150] += [0.05, 0, 0]
    result = det.detect(scan)
    print(f"Defect: {result['verdict']} ({result['confidence']})")


if __name__ == "__main__":
    main()
