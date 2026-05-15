# Selector Vs Single Best Vs Virtual Best

Selector performance compared with the single-best and virtual-best baselines.

| Result Scope | Method | Reference Solver Name | Average Objective | Objective Gap Vs Virtual Best | Objective Gap Vs Single Best | Classification Accuracy | Balanced Accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| real | selector | NA | 30.7593 | 0 | 0 | 1 | NA |
| real | single_best_solver | simulated_annealing_baseline | 30.7593 | 0 | 0 | NA | NA |
| real | virtual_best_solver | oracle | 30.7593 | 0 | 0 | NA | NA |
| synthetic | selector | NA | 16.1519 | 0 | 0 | 1 | NA |
| synthetic | single_best_solver | cpsat_round_robin | 16.1519 | 0 | 0 | NA | NA |
| synthetic | virtual_best_solver | oracle | 16.1519 | 0 | 0 | NA | NA |
