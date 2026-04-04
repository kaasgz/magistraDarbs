# Sports Tournament Scheduling Algorithm Selection

## Purpose

This repository contains the practical implementation for a master's thesis on
algorithm selection in sports tournament scheduling. The project focuses on
RobinX / ITC2021 sports timetabling instances and studies whether structural
characteristics of an instance can be used to predict which scheduling approach
is likely to perform best.

The workflow covered by the repository is:

1. parse sports timetabling instances
2. extract structural features
3. run a small portfolio of scheduling solvers
4. build an algorithm selection dataset
5. train and evaluate a selector model

## Project Structure

- `configs/` - YAML configuration files for benchmark and selector workflows.
- `configs/feature_config.yaml` - YAML configuration for reproducible feature-table generation.
- `data/raw/real/` - real RobinX / ITC2021 benchmark XML files added manually.
- `data/raw/synthetic/` - synthetic XML files used for development, smoke tests, and the local dashboard.
- `data/processed/` - derived datasets such as feature tables and selection datasets.
- `data/results/` - benchmark outputs, trained models, evaluation reports, and plots.
- `docs/feature_manifest.md` - documented definitions of the structural features used in the selection pipeline.
- `docs/selection_methodology.md` - concise note on target definition, split logic, leakage avoidance, SBS, and VBS.
- `notebooks/` - exploratory notebooks for analysis and thesis reporting.
- `src/parsers/` - XML parsing logic for sports timetabling instances.
- `src/features/` - structural feature extraction and feature-table construction.
- `src/solvers/` - baseline and optimization-based scheduling solvers.
- `src/selection/` - dataset building, selector training, evaluation, and analysis.
- `src/experiments/` - benchmark orchestration and experiment metrics.
- `src/utils/` - shared utility code.
- `tests/` - automated tests.
- `tests/fixtures/` - small synthetic fixtures used by tests.

## Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run tests:

```bash
pytest
```

Run the fast end-to-end smoke test for the full core pipeline:

```bash
pytest tests/test_core_pipeline_smoke.py -q
```

This tiny deterministic test generates a small synthetic batch, parses it,
extracts features, runs baseline benchmarks, builds the selection dataset,
trains the selector, and evaluates it end-to-end.

Run the local web dashboard:

```bash
python -m src.web.app
```

Generate demo instances and benchmark outputs immediately on startup:

```bash
python -m src.web.app --bootstrap-demo
```

## Workflow

Parse one instance and print a readable summary:

```bash
python -m src.main path/to/instance.xml
```

Build the structural feature table:

```bash
python -m src.features.build_feature_table --config configs/feature_config.yaml
```

This writes `data/processed/features.csv`.

Scan a folder of XML instances and build an intake inventory:

```bash
python -m src.parsers.instance_inventory data/raw/real --output data/processed/instance_inventory.csv
```

This writes `data/processed/instance_inventory.csv` and prints a parseability summary table.

Run benchmark experiments across multiple instances and solvers:

```bash
python -m src.experiments.run_benchmarks --config configs/benchmark_config.yaml
```

This writes `data/results/benchmark_results.csv`.

Build the algorithm selection dataset:

```bash
python -m src.selection.build_selection_dataset --config configs/selector_config.yaml
```

This writes `data/processed/selection_dataset.csv`.

Train the baseline selector model:

```bash
python -m src.selection.train_selector --config configs/selector_config.yaml
```

This saves the trained selector model and feature importance output under
`data/results/`.

Run a lightweight feature-group ablation study:

```bash
python -m src.selection.ablation_study --config configs/selector_config.yaml
```

This writes:

- `data/results/selector_ablation_summary.csv`
- `data/results/selector_ablation_regret.png`
- `data/results/selector_ablation_summary.md`

Evaluate the selector against algorithm-selection baselines:

```bash
python -m src.selection.evaluate_selector --config configs/selector_config.yaml
```

This writes:

- `data/results/selector_evaluation.csv`
- `data/results/selector_evaluation_summary.csv`
- `data/results/selector_evaluation_summary.md`

Export thesis-friendly tables and figures from the main experiment artifacts:

```bash
python -m src.experiments.reporting --output-dir data/results/thesis_artifacts
```

This writes:

- `data/results/thesis_artifacts/solver_comparison_table.csv`
- `data/results/thesis_artifacts/selector_vs_baselines_summary.csv`
- `data/results/thesis_artifacts/feature_importance_table.csv`
- `data/results/thesis_artifacts/solver_runtime_comparison.png`
- `data/results/thesis_artifacts/selector_objective_comparison.png`
- `data/results/thesis_artifacts/thesis_artifact_summary.md`

If your main experiment artifacts use non-default paths, pass them explicitly
with `--benchmark-csv`, `--evaluation-summary-csv`, and
`--feature-importance-csv`.

The benchmark and selector scripts use explicit YAML configuration files in
`configs/`. These files define paths, random seeds, time limits, selected
solvers, and model choices for reproducible experiment runs.

## Reproducible Runs

The repository now uses simple YAML configuration files to keep runs explicit
and reproducible.

- `configs/feature_config.yaml` controls feature-table inputs, outputs, and run metadata
- `configs/benchmark_config.yaml` controls instance paths, solver portfolio, seed, and time limit
- `configs/selector_config.yaml` controls selection-dataset paths, model artefacts, split settings, and evaluation outputs

Shared configuration concepts are grouped consistently:

- `paths`: input files, output files, and run-summary locations
- `run`: random seed and solver time limit
- `solvers`: selected solver names
- `split`: selector split strategy, test size, cross-validation folds, and repeats
- `selector`: selector model family
- `dataset`: dataset-build options such as per-solver objective columns

Each major CLI stage writes a sidecar run-summary JSON file. These files record:

- the stage name
- the timestamp
- the config path and config snapshot
- key settings such as seed, split, and solver list
- input and output artefact paths
- a compact summary of produced results

Typical reproducible workflow:

```bash
python -m src.features.build_feature_table --config configs/feature_config.yaml
python -m src.experiments.run_benchmarks --config configs/benchmark_config.yaml
python -m src.selection.build_selection_dataset --config configs/selector_config.yaml
python -m src.selection.train_selector --config configs/selector_config.yaml
python -m src.selection.ablation_study --config configs/selector_config.yaml
python -m src.selection.evaluate_selector --config configs/selector_config.yaml
python -m src.selection.error_analysis --config configs/selector_config.yaml
```

The local dashboard keeps using its own `demo_*` artefact namespace under
`data/processed/` and `data/results/`, so demo runs do not overwrite the main
thesis experiment outputs.

The default feature and benchmark configs now point to `data/raw/real`, so
mainline experiments do not silently consume synthetic dashboard data.

For the selector-specific methodological assumptions and leakage controls, see
`docs/selection_methodology.md`.

## Synthetic Data

The repository includes a synthetic instance generator for development, smoke
testing, controlled experiments, and the local dashboard.

- Synthetic instances are written to dedicated demo paths such as `data/raw/synthetic/demo_instances/`
- They are clearly marked as synthetic in both XML metadata and the generated manifest
- They are designed to be structurally plausible RobinX-like inputs for the parser and feature pipeline
- They are not a substitute for real RobinX / ITC2021 benchmark instances and should not be presented as equivalent empirical evidence

Keep synthetic and real benchmark artefacts separate when preparing thesis
experiments or reporting results.

## Adding Real Benchmark Instances

Add real RobinX / ITC2021 XML files manually under `data/raw/real/`. This
repository does not download benchmark data automatically.

Recommended intake workflow:

```bash
python -m src.parsers.instance_inventory data/raw/real --output data/processed/instance_inventory.csv
python -m src.features.build_feature_table --config configs/feature_config.yaml
python -m src.experiments.run_benchmarks --config configs/benchmark_config.yaml
```

Notes:

- keep real XML files under `data/raw/real/`
- keep generated or demo XML files under `data/raw/synthetic/`
- do not point the main feature or benchmark pipelines at a mixed `data/raw/` folder
- if you want to inspect synthetic files, run the inventory helper on `data/raw/synthetic/` separately

## Web Dashboard

The repository now includes a lightweight Python-only web interface for local
inspection of the full workflow. It does not require extra web dependencies.

- It is for thesis demos, parser walkthroughs, and synthetic smoke runs.
- It is not the main thesis experiment pipeline and should not be used as the authoritative source for final benchmark reporting.
- It keeps real-instance inspection separate from synthetic demo execution.

- Start the server with `python -m src.web.app`
- Open `http://127.0.0.1:8000/`
- Use `Load Real Instance` to inspect one XML from `data/raw/real/` and show its summary plus extracted structural features
- Use `Generate Synthetic Instance` to create one clearly labeled synthetic preview instance
- Use `Run Synthetic Demo Pipeline` to create synthetic RobinX-like instances, build features, run solver benchmarks, train the selector, and inspect the generated tables
- For a one-command bootstrap, use `python -m src.web.app --bootstrap-demo`

The dashboard writes dedicated demo artifacts so it does not overwrite the main
CLI outputs. Real-instance inspection does not overwrite thesis experiment files,
and synthetic dashboard outputs stay in dedicated `demo_*` paths or synthetic-only
folders:

- `data/raw/real/` is read for real-instance inspection only
- `data/raw/synthetic/demo_preview/`
- `data/raw/synthetic/demo_instances/`
- `data/processed/demo_preview_manifest.json`
- `data/processed/demo_manifest.json`
- `data/processed/demo_features.csv`
- `data/processed/demo_selection_dataset.csv`
- `data/results/demo_benchmark_results.csv`
- `data/results/demo_selector.joblib`
- `data/results/demo_feature_importance.csv`
- `data/results/demo_selector_evaluation.csv`

If `python` resolves to a Windows Store alias on your system, use the installed
interpreter directly or adjust your `PATH` to point to a real Python
installation.
