# Solver Comparison Table

Aggregated solver coverage, objective, runtime, and win-count metrics.

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
