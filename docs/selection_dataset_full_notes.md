# Full Selection Dataset Notes

This file is kept as a short pointer for older references. The current mixed
dataset contract is documented in
[docs/full_selection_dataset.md](full_selection_dataset.md), and the full
from-zero command sequence is documented in
[docs/reproduction_guide.md](reproduction_guide.md).

Current default inputs:

| Source | Features | Benchmarks |
| --- | --- | --- |
| Real | `data/processed/real_pipeline_current/features.csv` | `data/results/real_pipeline_current/benchmark_results.csv` |
| Synthetic | `data/processed/synthetic_study/features.csv` | `data/results/synthetic_study/benchmark_results.csv` |

Current default output:

```text
data/processed/selection_dataset_full.csv
```

Use:

```powershell
.\.venv\Scripts\python.exe -m src.selection.build_selection_dataset_full
```
