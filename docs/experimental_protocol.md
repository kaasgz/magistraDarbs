# Experimental Protocol

This note summarizes the artifact separation and interpretation rules used by
the thesis experiments. For the full from-zero command sequence, see
[`docs/reproduction_guide.md`](reproduction_guide.md).

## Artifact Scopes

| Scope | Main inputs | Main outputs | Purpose |
| --- | --- | --- | --- |
| Refreshed real data | `data/raw/real/` | `data/processed/real_pipeline_current/`, `data/results/real_pipeline_current/` | Current-code rerun on RobinX / ITC2021 XML instances |
| Synthetic study | `data/raw/synthetic/study/` | `data/processed/synthetic_study/`, `data/results/synthetic_study/` | Multi-seed controlled benchmark study |
| Mixed selection dataset | Refreshed real and synthetic study outputs | `data/processed/selection_dataset_full.csv`, `data/results/full_selection/` | Combined selector data and optional mixed selector evaluation |
| Thesis reports | Refreshed real, synthetic study, and mixed selector artifacts | `data/results/reports/` | Coverage-aware tables and Markdown summaries |
| Local dashboard demo | `data/raw/synthetic/demo_*` | `demo_*` files under `data/processed/` and `data/results/` | Lightweight localhost demonstrations only |

The localhost dashboard reads generated thesis artifacts but does not run the
real, synthetic-study, mixed-dataset, or thesis-report pipelines on page load.
Demo actions write only to the isolated demo namespace.

## Recommended Order

1. Run the current real-data pipeline.
2. Build the real solver compatibility matrix.
3. Generate or refresh the larger synthetic study dataset.
4. Run the synthetic study benchmark pipeline.
5. Build `selection_dataset_full.csv`.
6. Train and evaluate the selector on the full mixed dataset.
7. Generate thesis reports under `data/results/reports/`.
8. Generate thesis-facing tables, figures, and validation artifacts.
9. Use the dashboard only to inspect the generated artifacts.

## Reporting Rules

- Report synthetic and real scopes separately unless the table is explicitly
  about the mixed selector dataset.
- Report solver support and scoring status next to performance summaries.
- Compare objective values only when `objective_value_valid` is true.
- Treat partial-support objectives as implementation-level diagnostic results,
  not complete RobinX / ITC2021 objective values.
- Treat Timefold `not_configured` rows as explicit missing external-solver
  configuration, not as silent failures.
- Keep legacy artifacts separate from refreshed outputs so reruns remain
  reproducible and old files are not silently overwritten.
