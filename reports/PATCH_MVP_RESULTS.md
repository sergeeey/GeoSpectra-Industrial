# Patch MVP Results

## Patch Architecture Validation

### Detection Rates by Defect Size

| Defect Size | Detection Rate | Notes |
|-------------|---------------|-------|
| 1% | 75% | Below validated range for reliable detection |
| 5% | 100% | Reliable detection threshold |
| 10% | 100% | Always detected |
| 20% | 100% | Always detected |

### Key Findings

- **ADR-IND-008**: Patch architecture with FPS sampling + kNN patches + top-k mean aggregation is effective for local defect detection
- **ADR-IND-009**: Hierarchical detector (global + patch) outperforms either layer alone
- **ADR-IND-011**: Rule-based override (patch high → LOCAL_DEFECT) preserves local signal better than weighted sum

### Limitations

- 1% defects: 75% detection — acceptable for MVP but needs improvement for production
- Requires registration for reliable operation (ADR-IND-012)
- No defect localization without Mode B (ADR-IND-018)
