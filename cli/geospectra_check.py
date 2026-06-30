"""Command-line interface for GeoSpectra defect detection.

Usage:
    python -m cli.geospectra_check reference.stl scan.ply
"""

import argparse
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.loaders import load_pointcloud
from core.two_mode_detector import TwoModeDetector


def main():
    parser = argparse.ArgumentParser(description="GeoSpectra 3D defect detection")
    parser.add_argument("reference", help="Reference 3D scan file")
    parser.add_argument("scan", help="Test 3D scan file")
    parser.add_argument("--mode", choices=["A", "B", "auto"], default="auto",
                       help="Detection mode (default: auto)")
    parser.add_argument("--save", help="Save result to JSON file")
    args = parser.parse_args()
    
    print(f"Loading reference: {args.reference}")
    ref_points = load_pointcloud(args.reference)
    if ref_points is None:
        print("ERROR: Failed to load reference")
        sys.exit(1)
    print(f"  {len(ref_points)} points loaded")
    
    print(f"Loading scan: {args.scan}")
    scan_points = load_pointcloud(args.scan)
    if scan_points is None:
        print("ERROR: Failed to load scan")
        sys.exit(1)
    print(f"  {len(scan_points)} points loaded")
    
    print(f"\nFitting detector (mode={args.mode})...")
    detector = TwoModeDetector(mode=args.mode)
    detector.fit(ref_points)
    
    print("Running detection...")
    result = detector.detect(scan_points)
    
    print(f"\n{'='*50}")
    print(f"VERDICT: {result['verdict']}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"Anomaly Score: {result['anomaly_score']:.3f}")
    print(f"Mode Used: {result['mode_used']}")
    print(f"Runtime: {result.get('runtime_ms', 'N/A')} ms")
    print(f"{'='*50}")
    
    if args.save:
        with open(args.save, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nResult saved to: {args.save}")


if __name__ == "__main__":
    main()
