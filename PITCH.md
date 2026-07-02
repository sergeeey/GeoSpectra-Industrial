# ScanGuard by GeoSpectra

## One-Minute Pitch

**Problem:** 3D scanning produces defects that human inspectors miss — especially on complex curved surfaces. Existing solutions require expensive CT scanners or trained operators.

**Solution:** ScanGuard uses spectral geometry (graph Laplacian eigenvalues) to fingerprint 3D surfaces. Any deviation from the golden reference triggers an actionable alert.

**Two-Mode Architecture:**
- **Mode A**: Drop a scan in any orientation — get pass/fail in 0.3 seconds
- **Mode B**: Need exact defect location? ICP alignment gives precise coordinates in 1.1 seconds
- **Auto**: System picks the right mode — 38% faster than always using precise mode

**Validated On:** 10 defect types × 5 industrial mesh types = 50 synthetic scenarios.
- **0% false positives** on clean scans (rotation/translation/scale variants) — [VALIDATED, 8 seeds, reproducible]
- Detection sensitivity on synthetic data: geometry and sampling-dependent — real-world threshold established during pilot calibration
- Pilot success criteria: <5% FP rate, >80% detection on known-defective scans (see PILOT_PROPOSAL.md)

**Status:** Pilot-ready. Seeking first manufacturing partner to establish real-world detection baseline.

**Contact:** See OUTREACH_PLAN.md
