# Test Quality Audit

This note records the current test coverage for the practical thesis
implementation and the most important remaining risks.

## Covered Flows

- Parsing and input hygiene: RobinX parsing, missing sections, instance
  inventory, feature-table construction, and source-folder validation.
- Feature extraction: core structural features, feature validation, synthetic
  generator determinism, and synthetic study generation.
- Solver execution: random baseline, CP-SAT compact model, simulated annealing
  baseline, Timefold adapter/wrapper, solver registry, compatibility matrix,
  and the shared scoring contract.
- Benchmark artifacts: benchmark runner, full benchmark wrapper, benchmark
  validation, reporting tables, and coverage-aware thesis report generation.
- Selection dataset: single-source dataset construction, refreshed mixed
  real/synthetic dataset construction, target tie-breaking, unsupported solver
  exclusion, leakage-safe model preparation, and full-dataset CLI mode.
- Model training and evaluation: Random Forest training, feature importance,
  repeated validation, SBS/VBS comparison, source-grouped full evaluation, and
  missing-objective fallback behavior.
- UI and thesis artifacts: dashboard state, presentation sections, generated
  figures, thesis tables, document extraction, and safe static-file serving.

## Tests Added In This Audit

- Solver registry metadata is now tested so every registered solver has a
  conservative thesis-facing role and maturity label.
- Full dataset CLI mode is tested against the refreshed
  `build_selection_dataset_full` path, including benchmark metadata columns.
- Dashboard solver tables are tested for role/interpretation fields so the UI
  distinguishes diagnostic baselines, partial models, heuristics, and external
  integrations.

## Remaining Testing Risks

- Most tests still use compact synthetic fixtures, not a broad set of real
  RobinX / ITC2021 namespace and constraint variants.
- Long-running thesis-scale benchmark reproduction is not part of the fast
  unit-test suite; it should remain a manual or scheduled regression check.
- Timefold correctness cannot be fully tested without a configured external
  executable and a documented external constraint model.
- Source-holdout evaluation is documented as a methodological improvement, but
  it is not yet implemented as a first-class testable evaluation mode.
- The UI tests validate dashboard payload structure, not pixel-perfect browser
  rendering.

## Recommended Command Set

Fast smoke check:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_core_pipeline_smoke.py -q
```

Focused audit regression set:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_solver_registry.py tests/test_scoring_contract.py tests/test_build_selection_dataset_full.py tests/test_build_selection_dataset.py tests/test_train_selector.py tests/test_evaluate_selector.py tests/test_web_dashboard.py -q
```

Full suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
