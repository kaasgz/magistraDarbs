# Selector Evaluation Summary

- Split strategy: `repeated_stratified_kfold`
- Validation splits: `9`
- Leakage control: training excludes benchmark-derived `objective_*` columns and computes SBS on the training partition only.
- Interpretation: objectives are compared inside the current target policy; support and scoring-status columns must be read before making broader solver-quality claims.

| Metric | Mean | Std |
| --- | ---: | ---: |
| classification_accuracy | 0.9957 | 0.0064 |
| balanced_accuracy | 0.9907 | 0.0139 |
| average_selected_objective | 19.5256 | 0.7302 |
| average_virtual_best_objective | 19.5128 | 0.7209 |
| average_single_best_objective | 19.9017 | 0.7098 |
| regret_vs_virtual_best | 0.0128 | 0.0192 |
| delta_vs_single_best | -0.3761 | 0.0570 |
| improvement_vs_single_best | 0.3761 | 0.0570 |

## Metrics By Dataset Type

| Dataset Type | Accuracy | Balanced Accuracy | Selected Objective | Regret Vs VBS | Delta Vs SBS |
| --- | ---: | ---: | ---: | ---: | ---: |
| real | 0.9815 | NA | 30.8148 | 0.0556 | -1.6296 |
| synthetic | 1.0000 | NA | 16.1389 | 0.0000 | 0.0000 |
