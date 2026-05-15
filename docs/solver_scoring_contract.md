# Solver Scoring Contract

This repository uses a common solver-result contract so benchmark outputs can
be interpreted without treating unsupported or partial runs as full objective
measurements. The contract is implemented in `src/solvers/base.py` and is
propagated by benchmark exports such as `data/results/real_pipeline_current/`,
`data/results/synthetic_study/`, and `data/results/reports/`.

## Objective Semantics

- `objective_value` is interpreted as lower-is-better throughout the
  repository.
- `objective_sense` is therefore `lower_is_better`.
- `objective_value_valid` states whether `objective_value` is a fully
  comparable objective under the implemented solver model.
- A row is objective-comparable only when it is feasible, has a numeric
  objective, and has `scoring_status = supported_feasible_run`.
- Partially modeled rows may contain an objective value, but that value is a
  simplified-model score rather than full RobinX / ITC2021 performance.
- Unsupported, failed, and not-configured rows must not be used as valid
  objective results.

## Benchmark Metadata Columns

Benchmark CSV files include the execution columns used by earlier pipeline
stages plus explicit scoring metadata:

| Column | Meaning |
| --- | --- |
| `solver_support_status` | Whether the solver's implemented model supports the parsed instance structure |
| `scoring_status` | How the row should be interpreted for objective comparison |
| `modeling_scope` | Short text describing the solver model used for the run |
| `scoring_notes` | Human-readable limitation, failure, or configuration notes |
| `objective_sense` | Objective direction, currently always `lower_is_better` |
| `objective_value_valid` | Boolean flag for fully comparable objective values |

## Portfolio Role Versus Run Status

Solver role is a property of the registered portfolio entry. Run status is a
property of one solver-instance execution. Keep these separate:

- `random_baseline` is a diagnostic baseline even when it returns a feasible
  placeholder row.
- `cpsat_solver` is a compact optimization baseline; it is only `supported`
  when the parsed instance stays inside the implemented compact model.
- `simulated_annealing_solver` is a simplified heuristic baseline; feasible
  rows can still be `partially_modeled_run`.
- `timefold` is an external integration point; `not_configured` means the
  executable is absent, not that a bundled solver failed.

The canonical registry metadata lives in `src/solvers/registry.py` and is used
by the dashboard and thesis tables.

## Solver Support Status

| Status | Interpretation |
| --- | --- |
| `supported` | The implemented solver model covers the parsed structure without known unmodeled constraint families |
| `partially_supported` | The solver can process the instance only under simplifying assumptions |
| `unsupported` | The parsed instance requires structure outside the solver's current model |
| `not_configured` | An external solver is unavailable, for example Timefold without an executable path |
| `failed` | The solver or external process failed operationally |

## Scoring Status

| Status | Objective interpretation |
| --- | --- |
| `supported_feasible_run` | Feasible result from a supported model; eligible for valid objective averages |
| `supported_infeasible_run` | Supported model, but no feasible solution was returned |
| `partially_modeled_run` | Feasible or diagnostic result from an incomplete model; not a full comparable objective |
| `unsupported_instance` | Solver explicitly does not support the parsed instance |
| `failed_run` | Solver execution failed before returning a valid result |
| `not_configured` | External solver was not configured |

Report-generation code may label older benchmark inputs as
`legacy_feasible_run` or `legacy_infeasible_run` when the original CSV predates
this contract. Those labels are compatibility annotations, not formal solver
statuses for new runs.

## Coverage-Aware Reporting

The thesis-facing report generator `src.experiments.thesis_report` separates
coverage from objective quality:

- Feasible coverage counts rows or instances where a solver returned a feasible
  result.
- Valid feasible coverage counts feasible rows or instances whose
  `objective_value_valid` flag is true.
- Average objective is computed only on valid feasible rows.
- Average runtime is computed on all recorded rows, including unsupported,
  failed, and not-configured outcomes.
- The support summary reports `solver_support_status` and `scoring_status`
  counts separately from performance quality.

This means a solver can have high feasible coverage but low valid feasible
coverage if it only solves a simplified model. Such rows are useful for
diagnostics and algorithm-selection experiments, but they must not be presented
as complete RobinX / ITC2021 objective performance.

## Selection Dataset Interpretation

The mixed selection dataset at `data/processed/selection_dataset_full.csv`
excludes unsupported, failed, and not-configured solver rows from target
selection. It also records support coverage columns, including
`benchmark_solver_support_coverage`,
`benchmark_best_solver_support_status`, and
`benchmark_best_solver_scoring_status`.

Partially supported solver rows remain visible in the data because they can be
useful for studying the implemented portfolio. When writing thesis results,
distinguish between the selector target used for the current implementation and
the stricter valid-objective interpretation used by coverage-aware reports.

## Practical Reading Rule

For thesis tables, read solver results in this order:

1. Check `solver_support_status` and `scoring_status`.
2. Check feasible coverage and valid feasible coverage.
3. Compare average objective only for valid feasible rows.
4. Use runtime averages as operational cost, not as proof of modeling support.
5. Treat `not_configured` as a documented absence of an external solver, not as
   a failed experiment.
