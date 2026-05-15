# Full Selection Dataset

This note documents the mixed real/synthetic algorithm-selection dataset written
to `data/processed/selection_dataset_full.csv`.

For the full command sequence, see
[docs/reproduction_guide.md](reproduction_guide.md).

## Current Inputs

The default full-dataset builder reads the refreshed thesis artifact namespaces:

| Source | Features | Benchmarks |
| --- | --- | --- |
| Real | `data/processed/real_pipeline_current/features.csv` | `data/results/real_pipeline_current/benchmark_results.csv` |
| Synthetic | `data/processed/synthetic_study/features.csv` | `data/results/synthetic_study/benchmark_results.csv` |

Run it with:

```powershell
.\.venv\Scripts\python.exe -m src.selection.build_selection_dataset_full
```

The generic builder CLI also delegates its `--full` mode to the refreshed
builder, so this compatibility command is equivalent:

```powershell
.\.venv\Scripts\python.exe -m src.selection.build_selection_dataset --full
```

## Output

Main output:

```text
data/processed/selection_dataset_full.csv
```

Sidecar summary:

```text
data/processed/selection_dataset_full_run_summary.json
```

The current thesis-scale dataset contains 234 rows: 54 real instances and 180
synthetic instances. It exposes 25 shared structural feature columns for model
training.

## Row Inclusion

- Each synthetic feature row becomes one output row with `dataset_type = synthetic`.
- Each real feature row becomes one output row with `dataset_type = real`.
- Feature rows are retained even when no solver has an eligible target result.
- Rows without an eligible target keep a missing `best_solver`.
- The feature schema is the intersection of synthetic and real feature columns.

The shared-schema rule keeps selector training consistent across both sources.

## Target Policy

The supervised target column is `best_solver`.

For each instance, a solver row can determine the target only when it has:

- `feasible = true`
- a numeric `objective_value`
- no unsupported, not-configured, or failed status in solver support, scoring,
  or run-status metadata

Rows marked `unsupported`, `not_configured`, `unsupported_instance`,
`failed_run`, `NOT_CONFIGURED`, `UNSUPPORTED_INSTANCE`, or failed execution are
kept for auditability, but excluded from target determination.

Partially modeled or simplified baseline rows are not hidden. They can remain
eligible when feasible and numeric, but their support status is exposed through
benchmark metadata columns such as:

- `benchmark_solver_support_coverage`
- `benchmark_best_solver_support_status`
- `benchmark_best_solver_scoring_status`

## Synthetic Multi-Seed Aggregation

The synthetic study may contain repeated benchmark rows for the same
`(instance_name, solver)` pair across benchmark seeds. Before target selection,
eligible synthetic rows are aggregated to one candidate per instance and solver:

1. mean objective value
2. mean runtime
3. number of eligible runs

The target is then selected from those per-solver aggregates.

## Tie Handling

Ties are resolved deterministically:

1. lower mean objective value
2. lower mean runtime
3. lexicographically smaller canonical solver name

Canonical solver names use `solver_registry_name` when available, otherwise
`solver_name`.

## Leakage Controls

The output includes audit metadata columns prefixed with `benchmark_`,
`objective_`, `label_`, and `target_`. These columns are not structural
pre-solving features.

Selector preparation excludes these columns from model input. It also excludes
`dataset_type`, source/provenance columns, solver status columns, scoring
columns, runtime columns, prediction columns, and post-evaluation metric
columns. These values are retained only for audit, grouped reporting, or
artifact traceability.

## Training And Evaluation

Train and evaluate the mixed selector with:

```powershell
.\.venv\Scripts\python.exe -m src.selection.train_selector --full-dataset
.\.venv\Scripts\python.exe -m src.selection.evaluate_selector --full-dataset
```

Outputs are written under:

```text
data/results/full_selection/
```

Important outputs:

- `random_forest_selector.joblib`
- `feature_importance.csv`
- `selector_evaluation.csv`
- `selector_evaluation_summary.csv`
- `selector_evaluation_summary.md`
- `selector_evaluation_run_summary.json`
- `combined_benchmark_results.csv`

The evaluation summary includes overall metrics and metrics grouped by
`dataset_type`, so real and synthetic behavior can be reported separately.
