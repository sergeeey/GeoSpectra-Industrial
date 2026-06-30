"""Demo: Aerospace bracket inspection with Mode A and Mode B.

Usage: python examples/demo_aerospace_bracket.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import trimesh

from core.two_mode_detector import TwoModeDetector


def main():
    # Create bracket mesh
    base = trimesh.creation.box(extents=[4.0, 0.4, 2.5])
    rib = trimesh.creation.box(extents=[0.4, 1.5, 2.5])
    rib.apply_translation([0, 0.8, 0])
    bracket = trimesh.util.concatenate([base, rib])
    
    ref_points = trimesh.sample.sample_surface(bracket, 2048)[0]
    
    # Create defective version (dent on one side)
    defective_bracket = base.copy()
    # Remove material from corner (simulated erosion)
    mask = (defective_bracket.vertices[:, 0] > 1.0) & (defective_bracket.vertices[:, 2] > 0.5)
    keep = defective_bracket.vertices[:, 0] < 1.5
    defective_bracket = defective_bracket.submesh([keep], append=True)
    
    try:
        scan_points = trimesh.sample.sample_surface(defective_bracket, 2048)[0]
    except Exception:
        scan_points = ref_points + np.random.normal(0, 0.05, ref_points.shape)
    
    print("=" * 50)
    print("AEROSPACE BRACKET INSPECTION")
    print("=" * 50)
    
    for mode in ["A", "B", "auto"]:
        detector = TwoModeDetector(mode=mode, n_patches=32, patch_size=64)
        detector.fit(ref_points)
        result = detector.detect(scan_points)
        print(f"\nMode {mode}: {result['verdict']} (conf={result['confidence']:.2f}, "
              f"score={result['anomaly_score']:.2f}, {result.get('runtime_ms', 'N/A')} ms)")


if __name__ == "__main__":
    main()
