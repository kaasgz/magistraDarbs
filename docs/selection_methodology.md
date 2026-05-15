# Selection Methodology

## Scope

This note documents the current algorithm selection methodology used in the
repository. It is intended to make the practical pipeline easier to justify and
reference in the thesis text.

## Target Definition

- The selector target is `best_solver`.
- `best_solver` is defined independently for each instance from benchmark
  results.
- Only feasible solver runs with a numeric `objective_value` are eligible.
- Lower objective values are treated as better.

## Tie Handling

When multiple solvers are equally good on one instance, the target is resolved
deterministically:

1. lower `objective_value`
2. lower `runtime_seconds`
3. lexicographically smaller `solver_name`

This makes label generation reproducible and auditable, even when benchmark
results contain ties.

## Split Logic

The selection pipeline supports three explicit split strategies:

- `holdout`
- `repeated_holdout`
- `repeated_stratified_kfold`

All splits are driven by the configured random seed. When stratification is not
feasible because the labeled dataset is too small or class counts are too low,
the code falls back explicitly to a non-stratified split and records a split
note in the run summary.

The default selector config uses repeated stratified cross-validation because
the selection dataset is typically small and a single holdout split is too
unstable for thesis reporting.

## Leakage Avoidance

The current implementation reduces leakage risk in the following ways:

- training uses only structural instance features
- benchmark-derived columns such as `objective_*` are excluded from selector
  training
- source-label metadata such as `dataset_type` is retained for auditing but is
  excluded from selector training by default
- source/provenance columns, solver status columns, scoring columns, runtime
  columns, prediction columns, and SBS/VBS/regret columns are also excluded by
  the central selector-preparation denylist
- selector predictions are evaluated out-of-sample on reproducible validation
  splits
- the SBS baseline is computed from the training partition only
- the VBS baseline is computed only from the test partition of each split

Important limitation:

- this methodology assumes that benchmark objective values are already on a
  solver-comparable scale
- if solver objective values are not genuinely comparable, then `best_solver`,
  SBS, VBS, and regret metrics should be interpreted only under the current
  scoring contract, not as a fully general claim

## SBS and VBS

- `SBS` (single best solver) is the single fixed solver selected from the
  training split using the benchmark aggregation rule from the experiment
  metrics helper
- `VBS` (virtual best solver) is the oracle baseline that chooses the best
  feasible solver separately for each test instance

These two baselines frame selector performance:

- SBS shows whether the selector beats a single fixed portfolio choice
- VBS shows the remaining gap to the ideal oracle policy

## Reported Metrics

The evaluation summary reports:

- classification accuracy
- balanced accuracy
- average selected objective
- average virtual-best objective
- average single-best objective
- regret vs virtual best
- delta vs single best

For convenience and backward compatibility, the detailed report also keeps
`improvement_vs_single_best`, which is simply the negative of `delta_vs_single_best`.

## Combined Synthetic and Real Dataset

The full dataset builder combines refreshed real-data artifacts and synthetic
study artifacts into `data/processed/selection_dataset_full.csv`.

- rows are labeled with `dataset_type = synthetic` or `dataset_type = real`
- only feature columns shared by both sources are included
- solver labels use `solver_registry_name` when available, falling back to
  `solver_name`
- unsupported, failed, or not-configured solver rows are kept for auditability
  but cannot become `best_solver` unless they are feasible and have a numeric
  objective

See `docs/full_selection_dataset.md` for the detailed construction contract
and `docs/reproduction_guide.md` for the complete run order.

When the selector is trained or evaluated with `--full-dataset`, outputs are
written under `data/results/full_selection/`. The evaluation summary keeps the
standard overall rows and additionally writes `aggregate_dataset_type_mean` and
`aggregate_dataset_type_std` rows so synthetic and real performance can be
reported separately without changing the underlying split methodology.

## Current Methodological Limitations

The current full thesis dataset is useful as a bounded reproducible baseline
experiment, but it should not be over-interpreted as a final general
algorithm-selection benchmark.

- The active target space is narrower than the nominal solver portfolio. The
  portfolio contains four solver entries, but the current `best_solver` labels
  are concentrated in two solvers.
- The target labels are strongly aligned with `dataset_type`: synthetic
  instances currently resolve to `cpsat_solver`, while real instances resolve
  to `simulated_annealing_solver`.
- `dataset_type` itself is excluded from selector input, but structural
  features can still act as an indirect source proxy if real and synthetic
  instances occupy different parts of the feature space.
- Partially supported solver results are tracked explicitly and can be useful
  for a controlled thesis baseline, but SBS, VBS, regret, and `best_solver`
  must be interpreted under the current scoring contract.
- Repeated stratified validation gives a stable in-distribution estimate, but
  it does not fully answer whether the model generalizes across data sources.

## Strengthening Plan

The next academically stronger experiment should add:

- a source-holdout evaluation, for example train on synthetic and test on real,
  then report the reverse direction separately when feasible
- a grouped split by instance family or generator seed to reduce near-duplicate
  leakage between train and test folds
- a source-prediction diagnostic that measures whether structural features
  alone can predict `dataset_type`
- a sensitivity analysis where `best_solver` is rebuilt with partially
  supported solver results excluded
- at least one additional genuinely competitive solver configuration, ideally
  a fully configured Timefold model or a stronger local-search heuristic
- more real instances and synthetic instances designed to produce multiple
  competing best-solver labels inside each data source
