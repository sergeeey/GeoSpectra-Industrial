"""CLI for GeoSpectra ScanGuard inspection."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.loaders import load_pointcloud
from core.two_mode_detector import TwoModeDetector


def main():
    if len(sys.argv) < 3:
        print("Usage: python -m cli.geospectra_check <reference> <scan> [--mode A|B|auto]")
        sys.exit(1)
    
    ref_path = sys.argv[1]
    scan_path = sys.argv[2]
    
    mode = "auto"
    if "--mode" in sys.argv:
        mode = sys.argv[sys.argv.index("--mode") + 1]
    
    print(f"Loading reference: {ref_path}")
    ref = load_pointcloud(ref_path)
    if ref is None:
        print("Failed to load reference")
        sys.exit(1)
    
    print(f"Loading scan: {scan_path}")
    scan = load_pointcloud(scan_path)
    if scan is None:
        print("Failed to load scan")
        sys.exit(1)
    
    print(f"Fitting detector (mode={mode})...")
    det = TwoModeDetector(mode=mode)
    det.fit(ref)
    
    print("Detecting...")
    result = det.detect(scan)
    
    print("\n" + "=" * 50)
    print(f"Result: {result['verdict']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Anomaly Score: {result['anomaly_score']}")
    print(f"Mode Used: {result['mode_used']}")
    print(f"Runtime: {result.get('runtime_ms', 'N/A')} ms")
    print("=" * 50)
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
