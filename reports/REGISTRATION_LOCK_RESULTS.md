# Registration Lock Results — Phase 2.2

## Summary

Registration module successfully eliminates false positives from pose variation while maintaining detection capability.

### Results

| Transform | Without Registration | With Registration |
|-----------|---------------------|-------------------|
| 15° rotation | 100% FP | 0% FP |
| 45° rotation | 100% FP | 0% FP |
| 90° rotation | 100% FP | 0% FP |
| Translation (small) | 100% FP | 0% FP |
| Translation (large) | 100% FP | 0% FP |

### Key ADRs

- **ADR-IND-013**: Registration gate blocks patch layer if confidence < threshold
- **ADR-IND-014**: PCA coarse + ICP fine alignment handles up to 180° rotation
- **ADR-IND-015**: Confidence threshold 0.5 provides balanced trade-off

### Trade-offs

- Processing time increases from ~0.3s to ~1.1s per scan (with ICP)
- Heavy noise (1%) still produces 23% FP — coherence check needed
- Some scans may fail registration → UNRELIABLE_ALIGNMENT verdict
