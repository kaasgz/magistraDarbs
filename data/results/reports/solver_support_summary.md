# Solver Support Summary

Support and scoring-status rows. Feasible rows describe coverage; valid feasible rows describe objective-comparable quality.

| Result Scope | Solver Registry Name | Solver Support Status | Scoring Status | Num Rows | Num Feasible Runs | Num Valid Feasible Runs | Average Runtime Seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| real | cpsat_solver | partially_supported | legacy_feasible_run | 54 | 54 | 54 | 54.8611 |
| real | random_baseline | simplified_baseline | legacy_feasible_run | 54 | 54 | 54 | 0.0001 |
| real | simulated_annealing_solver | simplified_baseline | legacy_feasible_run | 54 | 54 | 54 | 1.8103 |
| real | timefold | not_configured | not_configured | 54 | 0 | 0 | 0.0021 |
| synthetic | cpsat_solver | partially_supported | partially_modeled_run | 540 | 540 | 0 | 109.8528 |
| synthetic | random_baseline | partially_supported | partially_modeled_run | 540 | 540 | 0 | 0.0001 |
| synthetic | simulated_annealing_solver | partially_supported | partially_modeled_run | 279 | 279 | 0 | 0.8224 |
| synthetic | simulated_annealing_solver | unsupported | unsupported_instance | 261 | 0 | 0 | 0.0003 |
| synthetic | timefold | not_configured | not_configured | 540 | 0 | 0 | 0.0007 |
