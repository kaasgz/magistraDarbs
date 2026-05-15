# Thesis Benchmark And Selector Report

## Synthetic/Real Separation

- Report scope: `mixed`
- Every generated CSV includes a `result_scope` column.
- When the input benchmark contains both synthetic and real rows, solver metrics are grouped separately by `result_scope`.

## Inputs

- Benchmark results (real_benchmark_csv): `data/results/real_pipeline_current/benchmark_results.csv`
- Benchmark results (synthetic_benchmark_csv): `data/results/synthetic_study/benchmark_results.csv`
- Selector evaluation summaries (real_evaluation_summary_csv): `data/results/real_pipeline_current/selector_evaluation_summary.csv`
- Selector evaluation summaries (synthetic_evaluation_summary_csv): `data/results/synthetic_study/aggregate_selector_summary.csv`
- Feature importance: `not provided`

## Solver Comparison Table

| Result Scope | Solver Registry Name | Solver Name | Num Instances Total | Feasible Coverage Ratio | Valid Feasible Coverage Ratio | Win Count | Average Objective Valid Feasible | Average Runtime Seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| real | simulated_annealing_solver | simulated_annealing_baseline | 54 | 1 | 1 | 54 | 30.7593 | 1.8103 |
| real | cpsat_solver | cpsat_round_robin | 54 | 1 | 1 | 0 | 32.4444 | 54.8611 |
| real | random_baseline | random_baseline | 54 | 1 | 1 | 0 | 1209.8246 | 0.0001 |
| real | timefold | timefold | 54 | 0 | 0 | 0 | NA | 0.0021 |
| synthetic | random_baseline | random_baseline | 180 | 1 | 0 | 0 | NA | 0.0001 |
| synthetic | cpsat_solver | cpsat_round_robin | 180 | 1 | 0 | 0 | NA | 109.8528 |
| synthetic | simulated_annealing_solver | simulated_annealing_baseline | 180 | 0.5167 | 0 | 0 | NA | 0.4251 |
| synthetic | timefold | timefold | 180 | 0 | 0 | 0 | NA | 0.0007 |

## Solver Support Summary

| Result Scope | Solver Registry Name | Solver Support Status | Scoring Status | Num Rows | Num Feasible Runs | Num Valid Feasible Runs | Row Ratio Within Solver |
| --- | --- | --- | --- | --- | --- | --- | --- |
| real | cpsat_solver | partially_supported | legacy_feasible_run | 54 | 54 | 54 | 1 |
| real | random_baseline | simplified_baseline | legacy_feasible_run | 54 | 54 | 54 | 1 |
| real | simulated_annealing_solver | simplified_baseline | legacy_feasible_run | 54 | 54 | 54 | 1 |
| real | timefold | not_configured | not_configured | 54 | 0 | 0 | 1 |
| synthetic | cpsat_solver | partially_supported | partially_modeled_run | 540 | 540 | 0 | 1 |
| synthetic | random_baseline | partially_supported | partially_modeled_run | 540 | 540 | 0 | 1 |
| synthetic | simulated_annealing_solver | partially_supported | partially_modeled_run | 279 | 279 | 0 | 0.5167 |
| synthetic | simulated_annealing_solver | unsupported | unsupported_instance | 261 | 0 | 0 | 0.4833 |
| synthetic | timefold | not_configured | not_configured | 540 | 0 | 0 | 1 |

## Win Counts Per Solver

| Result Scope | Solver Registry Name | Solver Name | Win Count |
| --- | --- | --- | --- |
| real | simulated_annealing_solver | simulated_annealing_baseline | 54 |
| real | cpsat_solver | cpsat_round_robin | 0 |
| real | random_baseline | random_baseline | 0 |
| real | timefold | timefold | 0 |
| synthetic | cpsat_solver | cpsat_round_robin | 0 |
| synthetic | random_baseline | random_baseline | 0 |
| synthetic | simulated_annealing_solver | simulated_annealing_baseline | 0 |
| synthetic | timefold | timefold | 0 |

## Average Objective Per Solver

| Result Scope | Solver Registry Name | Solver Name | Average Objective Valid Feasible | Num Instances Solved |
| --- | --- | --- | --- | --- |
| real | simulated_annealing_solver | simulated_annealing_baseline | 30.7593 | 54 |
| real | cpsat_solver | cpsat_round_robin | 32.4444 | 54 |
| real | random_baseline | random_baseline | 1209.8246 | 54 |
| real | timefold | timefold | NA | 0 |
| synthetic | cpsat_solver | cpsat_round_robin | NA | 0 |
| synthetic | random_baseline | random_baseline | NA | 0 |
| synthetic | simulated_annealing_solver | simulated_annealing_baseline | NA | 0 |
| synthetic | timefold | timefold | NA | 0 |

## Average Runtime Per Solver

| Result Scope | Solver Registry Name | Solver Name | Average Runtime Seconds | Num Runs |
| --- | --- | --- | --- | --- |
| real | random_baseline | random_baseline | 0.0001 | 54 |
| real | timefold | timefold | 0.0021 | 54 |
| real | simulated_annealing_solver | simulated_annealing_baseline | 1.8103 | 54 |
| real | cpsat_solver | cpsat_round_robin | 54.8611 | 54 |
| synthetic | random_baseline | random_baseline | 0.0001 | 540 |
| synthetic | timefold | timefold | 0.0007 | 540 |
| synthetic | simulated_annealing_solver | simulated_annealing_baseline | 0.4251 | 540 |
| synthetic | cpsat_solver | cpsat_round_robin | 109.8528 | 540 |

## Selector Vs Single Best Vs Virtual Best

| Result Scope | Method | Reference Solver Name | Average Objective | Objective Gap Vs Virtual Best | Objective Gap Vs Single Best | Classification Accuracy | Balanced Accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| real | selector | NA | 30.7593 | 0 | 0 | 1 | NA |
| real | single_best_solver | simulated_annealing_baseline | 30.7593 | 0 | 0 | NA | NA |
| real | virtual_best_solver | oracle | 30.7593 | 0 | 0 | NA | NA |
| synthetic | selector | NA | 16.1519 | 0 | 0 | 1 | NA |
| synthetic | single_best_solver | cpsat_round_robin | 16.1519 | 0 | 0 | NA | NA |
| synthetic | virtual_best_solver | oracle | 16.1519 | 0 | 0 | NA | NA |

## Feature Importance Summary

_No rows available._

## Interpretation Notes

- Lower objective values are treated as better.
- Feasible coverage counts whether a solver returned a feasible result for an instance.
- Valid feasible coverage counts whether the row is objective-comparable under the scoring contract.
- Average objective uses only valid feasible rows; unsupported, failed, and not-configured rows cannot improve objective quality.
- Average runtime uses all recorded solver rows, including unsupported, failed, and not-configured rows.
- Support-status tables report `solver_support_status` and `scoring_status` separately from performance quality.
- The virtual best solver is an oracle baseline and should be interpreted as a lower bound.
- The single best solver is the best fixed solver baseline from selector evaluation.
