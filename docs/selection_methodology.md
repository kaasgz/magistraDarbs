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
