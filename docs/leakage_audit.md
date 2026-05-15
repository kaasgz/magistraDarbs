# Leakage Audit

This note documents how selector features are filtered so benchmark results,
targets, labels, dataset origin, and post-evaluation metrics do not enter model
training.

## Current Conclusion

The selector model is prepared through `src.selection.modeling.prepare_selection_data`.
That function keeps `instance_name` only for traceability and `best_solver` only
as the target. It excludes leakage-prone columns before fitting the model.

Excluded groups include:

- `objective_*`, including per-solver benchmark objectives and objective
  metadata that should not be used in the current selector.
- `benchmark_*`, including support coverage and target-audit summaries.
- `label_*` and `target_*`, including target-construction metadata.
- `dataset_*`, `source_*`, `is_synthetic`, source paths, file paths, and
  generator/random seed columns.
- `solver_*`, `scoring_*`, support/status/runtime/feasibility columns, and
  error messages.
- Prediction and evaluation columns such as `selected_*`, `true_*`,
  `single_best_*`, `virtual_best_*`, `regret_*`, `delta_*`, and
  `improvement_*`.

The intended remaining feature set is made of pre-solving structural
descriptors such as team count, slot count, constraint counts, density ratios,
slot pressure, and constraint-diversity measures.

## Remaining Risk

The most important remaining risk is not direct leakage but source proxying.
Even when `dataset_type` is excluded, real and synthetic instances may occupy
different regions of the structural feature space. A model can therefore learn
patterns that partly identify the data source and, indirectly, the dominant
`best_solver` label for that source.

This does not invalidate the current proof-of-concept, but it limits how far
the result can be generalized.

## Stronger Checks To Add Next

- Source-holdout validation: train on synthetic and test on real, then report
  the reverse direction separately if enough labels exist.
- Grouped validation by instance family or synthetic generator seed.
- A source-prediction diagnostic: train a classifier to predict `dataset_type`
  from the structural features only. High source-prediction accuracy would
  quantify the proxy risk.
- A sensitivity run where partially supported solver rows are excluded from
  target construction.

## Regression Test

The direct leakage filter is covered by:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_selection_leakage.py -q
```
