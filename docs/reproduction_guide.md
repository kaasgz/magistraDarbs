# Reproduction Guide

This guide explains how to run the practical thesis implementation from a fresh
checkout, how to regenerate the final results, how to start the dashboard, and
which artifacts should be treated as final thesis outputs.

## 1. Prepare The Environment

Run from the repository root.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Verify the installation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_core_pipeline_smoke.py -q
```

The smoke test uses tiny generated fixtures. It is not the thesis experiment,
but it confirms that parsing, feature extraction, benchmarking, selector
training, and selector evaluation can run end-to-end.

## 2. Check Inputs

The final mixed experiment expects two input sources:

| Input source | Expected location | Notes |
| --- | --- | --- |
| Real RobinX / ITC2021 XML | `data/raw/real/` | Add real benchmark XML files manually. The repository does not download them. |
| Synthetic study XML | `data/raw/synthetic/study/` | Can be regenerated with the command below. |

The current thesis-scale run uses 54 real instances and 180 synthetic
instances. If the real XML files are missing, the real-data pipeline cannot
reproduce the final numbers.

## 3. Rebuild Final Thesis Results

Run the commands in this order. This is the canonical final-result sequence; do
not mix it with development shortcuts when reproducing the thesis numbers. The
full reproducibility contract is documented in
[docs/reproducibility_audit.md](reproducibility_audit.md).

```powershell
.\.venv\Scripts\python.exe -m src.experiments.generate_synthetic_dataset --n 180 --seeds 42,43,44 --output-root data\raw\synthetic\study
.\.venv\Scripts\python.exe -m src.experiments.run_real_pipeline_current --config configs\real_pipeline_current.yaml
.\.venv\Scripts\python.exe -m src.experiments.build_solver_compatibility_matrix
.\.venv\Scripts\python.exe -m src.experiments.run_synthetic_study --config configs\synthetic_study.yaml
.\.venv\Scripts\python.exe -m src.selection.build_selection_dataset_full
.\.venv\Scripts\python.exe -m src.selection.train_selector --full-dataset
.\.venv\Scripts\python.exe -m src.selection.evaluate_selector --full-dataset
.\.venv\Scripts\python.exe -m src.experiments.thesis_report
.\.venv\Scripts\python.exe -m src.thesis.generate_assets
```

What each stage does:

| Stage | Command module | Main output |
| --- | --- | --- |
| Synthetic XML generation | `src.experiments.generate_synthetic_dataset` | `data/raw/synthetic/study/` |
| Real-data rerun | `src.experiments.run_real_pipeline_current` | `data/processed/real_pipeline_current/`, `data/results/real_pipeline_current/` |
| Real solver compatibility | `src.experiments.build_solver_compatibility_matrix` | `data/processed/real_pipeline_current/solver_compatibility_matrix.csv` |
| Synthetic study benchmark | `src.experiments.run_synthetic_study` | `data/processed/synthetic_study/`, `data/results/synthetic_study/` |
| Mixed dataset build | `src.selection.build_selection_dataset_full` | `data/processed/selection_dataset_full.csv` |
| Mixed selector training | `src.selection.train_selector --full-dataset` | `data/results/full_selection/random_forest_selector.joblib` |
| Mixed selector evaluation | `src.selection.evaluate_selector --full-dataset` | `data/results/full_selection/selector_evaluation_summary.csv` |
| Thesis report tables | `src.experiments.thesis_report` | `data/results/reports/` |
| Thesis export assets | `src.thesis.generate_assets` | `data/results/thesis_tables/`, `data/results/figures/`, validation files |

The expected current run produces:

| Metric | Expected value |
| --- | --- |
| Mixed selection rows | 234 |
| Real instances | 54 |
| Synthetic instances | 180 |
| Structural selector features | 25 |
| Registered solver entries | 4 |
| Validation scheme | repeated 3x3 stratified validation |

## 4. Start The Dashboard

The dashboard reads existing artifacts. It does not run experiments on page
load.

```powershell
.\.venv\Scripts\python.exe -m src.web.app
```

Open:

```text
http://127.0.0.1:8000/
```

If the page looks stale, stop the old server process and start it again. The
dashboard is served from local files, so a running old process can keep serving
an older UI bundle.

The dashboard expects these artifacts to exist:

| Dashboard input | Produced by |
| --- | --- |
| `data/processed/selection_dataset_full.csv` | `src.selection.build_selection_dataset_full` |
| `data/results/full_selection/` | `train_selector --full-dataset`, `evaluate_selector --full-dataset` |
| `data/results/reports/` | `src.experiments.thesis_report` |
| `data/results/thesis_tables/` | `src.thesis.generate_assets` |
| `data/results/figures/` | `src.thesis.generate_assets` |
| `data/results/thesis_figures_index.md` | `src.thesis.generate_assets` |

The UI contains seven thesis-defense sections:

| Section | What it shows |
| --- | --- |
| `Eksperimentālās daļas uzbūve` | Dataset size, model type, validation setup, and the dataset-composition figure used in the thesis text. |
| `Datu un pazīmju sagatavošana` | Data sources, synthetic generation, XML parsing, and structural-feature extraction flow. |
| `Modeļa apmācība un novērtēšana` | Accuracy, balanced accuracy, regret, SBS/VBS comparison, and the SBS/VBS figure used in the thesis text. |
| `Risinātāju portfelis` | Solver roles, support/interpretation status, and best_solver class support. |
| `Eksperimentu rezultāti` | Feature importance and feature-group interpretation from the thesis results section. |
| `Datu grupu rezultāti` | Real-vs-synthetic result table described in the thesis text. |
| `Interpretācija un ierobežojumi` | The bounded interpretation and limitations stated in the thesis practical section. |
| `Praktiskās daļas īstenojums` | Implemented practical workflow steps and main result artifacts. |

The `Datu un pazīmju sagatavošana` section also includes a code map that links
the practical-workflow steps to the main implementation files in `src/`.
The final implementation section is a compact summary of what was built and
which files contain the main outputs.

## 5. Final Artifacts

Treat these as the final thesis-facing outputs:

| Artifact | Purpose |
| --- | --- |
| `data/processed/selection_dataset_full.csv` | Mixed real/synthetic algorithm-selection dataset. |
| `data/processed/selection_dataset_full_run_summary.json` | Dataset construction settings and row summaries. |
| `data/results/full_selection/random_forest_selector.joblib` | Trained mixed selector model. |
| `data/results/full_selection/feature_importance.csv` | Feature importance used in thesis figures and tables. |
| `data/results/full_selection/selector_evaluation.csv` | Detailed out-of-sample selector predictions. |
| `data/results/full_selection/selector_evaluation_summary.csv` | Main selector metrics, including source-group summaries. |
| `data/results/full_selection/selector_evaluation_summary.md` | Human-readable selector evaluation summary. |
| `data/results/full_selection/combined_benchmark_results.csv` | Canonical benchmark table for mixed selector evaluation. |
| `data/results/reports/*.csv` | Coverage-aware report tables for solver and selector comparison. |
| `data/results/reports/*.md` | Markdown versions of report tables. |
| `data/results/thesis_tables/*.csv` | Clean thesis-facing tables. |
| `data/results/thesis_tables/*.md` | Markdown table exports. |
| `data/results/figures/*.png` | Figures used by the dashboard and thesis review. |
| `data/results/thesis_text_validation.csv` | Statement-level validation table against repository artifacts. |
| `data/results/thesis_text_validation.md` | Readable validation report. |
| `data/results/thesis_data_references.json` | Mapping from thesis statements to source artifacts. |
| `data/results/thesis_figures_index.md` | Figure index used by the dashboard. |
| `magistra_darbs_with_data_refs.md` | Exported thesis text with data references. |

## 6. Useful Development Commands

Run all tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Run the general configured pipeline:

```powershell
.\.venv\Scripts\python.exe -m src.experiments.run_all_pipeline --with-inventory
```

Run a synthetic-only thesis-mode smoke pipeline:

```powershell
.\.venv\Scripts\python.exe -m src.experiments.run_thesis_pipeline --dataset-size 100 --time-limit-seconds 60 --seed 42
```

Inspect one XML instance:

```powershell
.\.venv\Scripts\python.exe -m src.main path\to\instance.xml
```

Bootstrap isolated dashboard demo artifacts:

```powershell
.\.venv\Scripts\python.exe -m src.web.app --bootstrap-demo
```

These development commands are useful for checking individual pieces. They are
not a substitute for the final reproduction order in section 3.

## 7. Interpretation Notes

- Keep real, synthetic, mixed, report, and demo outputs in their separate
  folders.
- Treat [docs/reproducibility_audit.md](reproducibility_audit.md) as the audit
  trail for seeds, inputs, outputs, command order, and known environment limits.
- Report solver support and scoring status next to objective values.
- Use only valid feasible objective rows for direct solver quality comparison.
- Treat `timefold` rows with `not_configured` as an explicit missing external
  executable, not as a solver failure.
- Treat the current result as a bounded reproducible baseline experiment, not
  as a claim that the portfolio is a complete ITC2021 competition-grade solver
  set.
