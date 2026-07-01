"""Session bootstrap for GeoSpectra-Industrial.

Recovers context when starting a new session.
Reads key files and prints project state.
"""

import json
from pathlib import Path


def bootstrap():
    root = Path(__file__).parent.parent
    
    print("=" * 60)
    print("GEOSPECTRA-INDUSTRIAL SESSION BOOTSTRAP")
    print("=" * 60)
    
    # Read project status
    status_path = root / "PROJECT_STATUS.md"
    if status_path.exists():
        lines = status_path.read_text().split("\n")[:20]
        for line in lines:
            print(line)
    
    # Read ADR summary
    adr_path = root / "ADR.md"
    if adr_path.exists():
        content = adr_path.read_text()
        n_adrs = content.count("ADR-IND-")
        print(f"\nADRs documented: {n_adrs}")
    
    # Check latest benchmark
    bench_path = root / "data" / "two_mode_integration.json"
    if bench_path.exists():
        data = json.loads(bench_path.read_text())
        print(f"\nLatest benchmark: {data.get('overall', 'N/A')}")
        print(f"Checks: {data.get('checks_passed', 0)}/{data.get('checks_total', 0)}")
    
    print("\n" + "=" * 60)
    print("Key files:")
    print("  core/two_mode_detector.py — unified detector")
    print("  core/patch_bank_detector.py — Mode A")
    print("  benchmarks/two_mode_integration.py — validation")
    print("  ADR.md — 20 architectural decisions")
    print("=" * 60)


if __name__ == "__main__":
    bootstrap()
