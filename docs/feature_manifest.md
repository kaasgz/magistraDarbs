# Feature Manifest

This document describes the structural features extracted by
`src/features/feature_extractor.py`.

Design principles:

- features are intentionally simple, typed, and auditable
- features describe instance structure, not benchmark outcomes
- missing metadata falls back to conservative defaults instead of inferred values
- parser recovery and parser notes remain audit artefacts and are not used as structural features

## Size Features

| Feature name | Type | Description | Formula / computation logic | Default / fallback behavior | Why it may matter for algorithm selection |
| --- | --- | --- | --- | --- | --- |
| `num_teams` | `int` | Number of teams in the instance. | Parser `team_count`. | `0` if no teams can be recovered. | Team count drives search-space size and symmetry. |
| `num_slots` | `int` | Number of slots or rounds. | Parser `slot_count`. | `0` if slots are missing. | Calendar length affects flexibility and feasibility pressure. |
| `num_constraints` | `int` | Number of parsed constraints. | Parser `constraint_count`. | `0` if constraints are missing. | Constraint volume is a coarse complexity proxy. |
| `teams_is_even` | `bool` | Whether the team count is even. | `num_teams > 0 and num_teams % 2 == 0`. | `False` when `num_teams == 0`. | Odd-team tournaments induce byes and a different round-robin structure. |
| `estimated_minimum_slots` | `int` | Estimated slot lower bound implied by team count and round-robin mode. | Single RR: `n` if `n` odd else `n - 1`; doubled when metadata mode is `double`. | `0` for `num_teams <= 1`; assumes single RR if mode is missing. | Gives a simple lower bound for calendar tightness. |
| `slot_pressure` | `float` | Lower-bound slot requirement relative to available slots. | `estimated_minimum_slots / num_slots`. | `0.0` when `num_slots == 0`. | High pressure suggests tighter feasibility and harder repair decisions. |
| `slot_surplus` | `int` | Available slots beyond the lower-bound requirement. | `max(0, num_slots - estimated_minimum_slots)`. | `0` when `num_slots <= estimated_minimum_slots`. | Extra slack can help constructive and local-improvement methods. |

## Constraint Composition Features

| Feature name | Type | Description | Formula / computation logic | Default / fallback behavior | Why it may matter for algorithm selection |
| --- | --- | --- | --- | --- | --- |
| `num_hard_constraints` | `int` | Number of constraints classified as hard. | Count constraints whose descriptors indicate hard type. | `0` if none can be identified. | Hard constraints dominate feasibility difficulty. |
| `num_soft_constraints` | `int` | Number of constraints classified as soft. | Count constraints whose descriptors indicate soft type. | `0` if none can be identified. | Soft constraints shape optimization trade-offs. |
| `num_unclassified_constraints` | `int` | Number of constraints not classified as hard or soft. | `num_constraints - num_hard_constraints - num_soft_constraints`, lower bounded at `0`. | `0` when all constraints are classified or no constraints exist. | High ambiguity weakens structural signal quality. |
| `num_constraints_missing_category` | `int` | Number of constraints without explicit category. | Count parsed constraints with empty `category`. | `0` when all categories are present. | Missing categories reduce interpretability of the constraint mix. |
| `num_constraints_missing_tag` | `int` | Number of constraints without explicit tag. | Count parsed constraints with empty `tag`. | `0` when all tags are present. | Missing tags remove fine-grained structural detail. |
| `num_constraints_missing_type` | `int` | Number of constraints without explicit type field. | Count parsed constraints with empty `type_name`. | `0` when all types are present. | Missing hard/soft typing makes feasibility-vs-objective structure less explicit. |

## Density Features

| Feature name | Type | Description | Formula / computation logic | Default / fallback behavior | Why it may matter for algorithm selection |
| --- | --- | --- | --- | --- | --- |
| `ratio_hard_to_all` | `float` | Share of constraints classified as hard. | `num_hard_constraints / num_constraints`. | `0.0` when `num_constraints == 0`. | Indicates how much of the instance is feasibility driven. |
| `ratio_soft_to_all` | `float` | Share of constraints classified as soft. | `num_soft_constraints / num_constraints`. | `0.0` when `num_constraints == 0`. | Indicates how much objective shaping exists. |
| `ratio_unclassified_to_all` | `float` | Share of constraints that remain unclassified. | `num_unclassified_constraints / num_constraints`. | `0.0` when `num_constraints == 0`. | Flags ambiguous or weakly specified constraint metadata. |
| `constraints_per_team` | `float` | Constraint count normalized by teams. | `num_constraints / num_teams`. | `0.0` when `num_teams == 0`. | Measures how much structural load falls on each team. |
| `constraints_per_slot` | `float` | Constraint count normalized by slots. | `num_constraints / num_slots`. | `0.0` when `num_slots == 0`. | Measures how densely the calendar is constrained over time. |
| `constraints_per_team_slot` | `float` | Constraint count normalized by the team-slot grid. | `num_constraints / (num_teams * num_slots)`. | `0.0` when `num_teams * num_slots == 0`. | Coarse proxy for overall structural density. |

## Diversity Features

| Feature name | Type | Description | Formula / computation logic | Default / fallback behavior | Why it may matter for algorithm selection |
| --- | --- | --- | --- | --- | --- |
| `number_of_constraint_categories` | `int` | Number of distinct constraint categories. | Count unique non-empty categories after case-insensitive normalization. | `0` when no categories are available. | More category variety suggests broader structural interactions. |
| `number_of_constraint_tags` | `int` | Number of distinct constraint tags. | Count unique non-empty tags after case-insensitive normalization. | `0` when no tags are available. | Separates homogeneous from heterogeneous constraint sets. |
| `number_of_constraint_types` | `int` | Number of distinct explicit constraint types. | Count unique non-empty `type_name` values after case-insensitive normalization. | `0` when no explicit types are available. | Distinguishes purely feasibility-driven from mixed-type instances. |
| `ratio_constraint_categories_to_constraints` | `float` | Distinct categories normalized by constraint count. | `number_of_constraint_categories / num_constraints`. | `0.0` when `num_constraints == 0`. | Normalizes category diversity by instance size. |
| `ratio_constraint_tags_to_constraints` | `float` | Distinct tags normalized by constraint count. | `number_of_constraint_tags / num_constraints`. | `0.0` when `num_constraints == 0`. | Captures whether the instance repeats a few motifs or many specific patterns. |
| `ratio_constraint_types_to_constraints` | `float` | Distinct explicit types normalized by constraint count. | `number_of_constraint_types / num_constraints`. | `0.0` when `num_constraints == 0`. | Quantifies how concentrated the explicit type labeling is. |

## Objective-Related Features

| Feature name | Type | Description | Formula / computation logic | Default / fallback behavior | Why it may matter for algorithm selection |
| --- | --- | --- | --- | --- | --- |
| `objective_present` | `bool` | Whether an objective label or sense was found. | `bool(objective_name or objective_sense)`. | `False` when both are missing. | Separates feasibility-only descriptions from explicitly optimization-oriented ones. |
| `objective_name` | `str` | Parsed objective label. | Normalized parser metadata `objective_name`. | Empty string when missing. | Different objective families may favor different solver designs. |
| `objective_sense` | `str` | Parsed optimization sense. | Normalized parser metadata `objective_sense`. | Empty string when missing. | Minimization and maximization tasks can encourage different search behavior. |
| `objective_is_minimization` | `bool` | Whether the objective sense indicates minimization. | `True` if `objective_sense` contains a minimization token. | `False` when missing or ambiguous. | A compact machine-readable objective-direction flag. |
| `objective_is_maximization` | `bool` | Whether the objective sense indicates maximization. | `True` if `objective_sense` contains a maximization token. | `False` when missing or ambiguous. | A compact machine-readable objective-direction flag. |
