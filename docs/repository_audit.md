# Repository Engineering Audit

Date: 2026-04-04

## Scope

This audit is based on a careful read of the current repository structure,
configuration, source modules, tests, and local dashboard code. No code
behavior was changed as part of this review.

## Executive Summary

The repository is in a strong prototype-to-thesis-transition state. The code is
modular, typed, readable, and unusually well tested for an academic project.
The pipeline separation is good: parsing, feature extraction, solver execution,
selection dataset construction, selector training, evaluation, error analysis,
and demo visualization are all in distinct modules with small public surfaces.

The main engineering risk is not code cleanliness. It is methodological
validity. The current benchmark/evaluation pipeline compares solver objective
values that are not on a common semantic scale. This means the current
`best_solver` labels can be invalid even if the code is internally consistent.
Related to that, the current solver portfolio mostly ignores the actual
RobinX/ITC2021 constraint structure, so the repository is currently better
described as a clean experimental scaffold than as a thesis-ready sports
timetabling study.

If the next phase focuses on objective comparability, richer instance
representation, stronger structural features, and a more defensible evaluation
protocol, this codebase can mature into a solid thesis implementation.

## Repository Overview

### Top-level structure

- `src/parsers/`: RobinX / ITC2021-like XML parsing into a typed summary object.
- `src/features/`: structural feature extraction and CSV feature table builder.
- `src/solvers/`: solver interface, registry, random baseline, CP-SAT baseline,
  and simulated annealing baseline.
- `src/experiments/`: benchmark runner and solver comparison metrics.
- `src/selection/`: selection dataset build, model training, evaluation, and
  error analysis.
- `src/demo/`: synthetic RobinX-like instance generation for demonstration.
- `src/web/`: lightweight local dashboard and static frontend assets.
- `configs/`: benchmark and selector YAML configs.
- `tests/`: broad unit-test coverage with synthetic fixtures.
- `data/`: currently empty except `.gitkeep`, which is good for a clean code
  repository but means there are no checked-in reference outputs.
- `notebooks/`: empty placeholder only.

### Main pipeline shape

1. Parse XML into `InstanceSummary`.
2. Extract flat structural features.
3. Run all selected solvers per instance.
4. Derive `best_solver` and optional per-solver objective columns.
5. Train a RandomForest selector.
6. Evaluate against single-best and virtual-best baselines.
7. Optionally analyze selector mistakes and visualize demo outputs in the local
   dashboard.

## Architectural Strengths

- Clear module boundaries. The separation between parser, features, solvers,
  experiments, selection, and dashboard code is clean and easy to reason about.
- Consistent CLI design. Each major stage exposes a focused entry point with
  straightforward arguments and config-file support.
- Good result normalization. `SolverResult` provides a simple shared contract
  across solver implementations.
- Reproducibility intent is visible. Seeds, deterministic ordering, stable CSV
  column ordering, and explicit config files are used throughout the pipeline.
- Tests are broad for a thesis prototype. There is coverage for parsing,
  features, solver registry behavior, benchmark execution, dataset building,
  training, evaluation, error analysis, demo generation, and dashboard service
  behavior.
- Dashboard separation is appropriate. Demo artifacts are written to dedicated
  `demo_*` paths and do not overwrite the main CLI experiment outputs.
- Import hygiene is mostly thoughtful. The lazy export approach in
  `src/selection/__init__.py` reduces accidental heavy imports.
- The code style matches the repository goals. Files are small, names are
  descriptive, and abstractions are restrained.

## Key Findings

### 1. Critical methodological issue: solver objectives are not comparable

Severity: Critical

The current portfolio does not optimize a shared scoring function:

- `random_baseline` returns a synthetic placeholder score based on counts and a
  random number.
- `cpsat_solver` minimizes the number of used slots in a simplified round-robin
  model.
- `simulated_annealing_solver` minimizes `1000 * team_conflict_penalty +
  used_slots`.

However, `src/experiments/metrics.py`,
`src/selection/build_selection_dataset.py`, and
`src/selection/evaluate_selector.py` all assume that lower
`objective_value` is directly comparable across solvers. That assumption is
false in the current implementation.

Impact:

- `best_solver` labels can be invalid.
- Single-best and virtual-best comparisons can be misleading.
- The selector may learn to predict artifacts of incompatible score scales
  rather than meaningful algorithm superiority.

This is the single biggest blocker for thesis-grade claims.

### 2. Current solvers do not reflect most of the parsed problem structure

Severity: High

The parser reads teams, slots, and constraints, but the current solver
implementations mostly ignore the actual RobinX/ITC2021 constraint content:

- CP-SAT only models one-match-per-pair and one-match-per-team-per-slot.
- Simulated annealing uses an inferred single round-robin representation and
  only penalizes team-slot conflicts plus slot usage.
- The random baseline is explicitly synthetic.

Impact:

- Constraint categories extracted from XML are largely irrelevant to solver
  behavior.
- The portfolio is not yet solving the same sports timetabling problem that the
  parser appears to describe.
- The algorithm selection task may be artificially easy or structurally
  disconnected from the intended thesis question.

### 3. Parser permissiveness can hide malformed input

Severity: High

`src/parsers/robinx_parser.py` uses `etree.XMLParser(recover=True)` inside
`load_instance()`. That is useful for resilience, but it also means malformed
XML can be silently repaired and passed downstream.

`src/features/build_feature_table.py` does strict pre-validation before parsing,
but `src/main.py` and `src/experiments/run_benchmarks.py` call `load_instance()`
directly without equivalent strict validation.

Impact:

- The benchmark pipeline may consume partially broken inputs without failing
  fast.
- Downstream datasets can contain silently corrupted instance summaries.
- Reproducing results from raw files becomes less trustworthy.

### 4. Feature space is currently too shallow for a strong thesis claim

Severity: High

The current feature set in `src/features/feature_extractor.py` is compact and
clean, but very limited:

- Mostly counts and ratios.
- Very coarse constraint statistics.
- No graph, density, symmetry, slot-pressure, or constraint-interaction
  features.
- No literature-backed structural descriptors yet.

Also:

- Objective-related fields are now populated when XML metadata provides them,
  but many instances may still omit explicit objective metadata.
- Hard/soft classification remains lightweight and metadata-driven, so
  partially specified constraints can still remain unclassified.

Impact:

- The selector may be learning from a feature space that is too weak to support
  meaningful conclusions.
- Reported importance rankings may overstate the value of very shallow
  descriptors.

### 5. Error analysis mixes structural and outcome variables

Severity: High

`src/selection/error_analysis.py` merges the evaluation report with the
selection dataset and then computes numeric "feature" differences for hard vs
non-hard instances. By default, the selection dataset includes `objective_*`
columns from benchmark results.

Those `objective_*` columns are not structural instance features, but
`_feature_pattern_summary()` currently treats them like numeric features.

Impact:

- The error-analysis plots can report solver outcome variables as if they were
  structural instance characteristics.
- This weakens thesis credibility and blurs the distinction between explanatory
  variables and benchmark targets.

### 6. Evaluation protocol is too thin for thesis-level evidence

Severity: Medium-High

The selector evaluation is currently based on a single train/test split with one
seed and one model family.

Missing pieces:

- repeated runs across seeds
- grouped or family-aware splits
- cross-validation
- confidence intervals or variance reporting
- ablation studies
- sensitivity analysis on feature subsets or solver portfolios

Impact:

- Reported performance can be unstable.
- It is hard to argue that observed gains are robust rather than split-specific.

### 7. Benchmark artifacts are too sparse for strong reproducibility

Severity: Medium

The main benchmark CSV contains only:

- `instance_name`
- `solver_name`
- `objective_value`
- `runtime_seconds`
- `feasible`
- `status`

Missing from main persisted artifacts:

- config snapshot
- seed
- solver hyperparameters
- software versions
- machine/environment metadata
- richer solver metadata or diagnostics

Impact:

- Reproducing a reported benchmark table later may require reconstructing hidden
  context from configs and code state.
- Diagnosing changes between runs will be harder than necessary.

### 8. Dependency set is heavier and looser than the current implementation needs

Severity: Medium

`requirements.txt` is unpinned and currently includes heavy packages that are
not yet central to the implemented pipeline, such as `xgboost` and
`jupyterlab`.

Impact:

- Environment recreation is less stable across time.
- Dependency footprint is larger than the current code path requires.
- This is slightly out of alignment with the repository principle of avoiding
  unnecessary heaviness.

### 9. Test coverage is broad, but still mostly toy-scale

Severity: Medium

The tests do a good job of protecting the current scaffold, but they mostly use
small synthetic examples.

Notable missing coverage:

- real RobinX/ITC2021 namespace variants and richer XML layouts
- malformed-but-recoverable XML behavior in the benchmark path
- full end-to-end pipeline reproducibility across repeated runs
- cases where all solvers fail on a test instance and evaluation means can
  become `NaN`
- HTTP-level tests for the dashboard server
- performance or time-limit regression tests on larger instances

Impact:

- The tests strongly validate the current toy semantics, but they do not yet
  validate the code against realistic thesis conditions.

### 10. Thesis messaging risk: the demo layer is polished, the scientific core is still baseline

Severity: Medium

The local dashboard is a nice communication tool and well isolated, but the
scientific core still relies on baseline solvers and simplified instance
semantics. The project currently presents very well as software, but it may
still read as methodologically underdeveloped if described too ambitiously in a
thesis.

Impact:

- Reviewers may perceive a mismatch between implementation polish and scientific
  depth if the current limitations are not explicitly stated.

## Reproducibility Assessment

### What is already good

- deterministic file ordering in dataset construction
- explicit seeds in configs and solver interfaces
- stable CSV column ordering
- fixed single-thread CP-SAT search
- demo artifacts separated from main outputs
- empty `data/` directories by default, which keeps the repository clean

### What is currently weak

- unpinned dependencies
- no locked environment file
- no benchmark manifest that records config plus environment plus commit
- tolerant XML parsing in some production paths
- single-split evaluation only
- no checked-in reference artifact for a known end-to-end run

## Testing Assessment

### Strong areas

- parser happy-path and sparse-path behavior
- feature extraction basics
- solver interface and registry
- baseline solver behavior
- benchmark runner behavior including failure handling
- dataset building and tie-breaking
- selector training and evaluation happy paths
- error analysis artifact creation
- demo generation and dashboard service bootstrap
- config-driven workflow execution

### Gaps worth addressing soon

- realistic XML fixture diversity
- end-to-end reproducibility tests over the full main pipeline
- evaluation edge cases with no feasible solver on test instances
- explicit tests that structural features, not `objective_*` columns, drive
  analysis tooling
- HTTP endpoint tests for `src/web/app.py`
- larger-instance smoke tests for runtime and memory stability

## Thesis Risks

These are the places most likely to look weak in a master's thesis if not
improved before final evaluation:

- The solver portfolio is not yet solving a common, fully specified objective.
- The parser and feature set expose more problem richness than the solvers
  currently use.
- The feature set is still too basic for strong algorithm selection claims.
- The evaluation protocol is too narrow for robust empirical evidence.
- Error analysis currently risks mixing structural features with benchmark
  outcomes.
- The random baseline is useful as plumbing, but weak as a thesis-facing member
  of the solver portfolio unless very clearly labeled as a placeholder sanity
  check.

## Prioritized Roadmap

### 1. Define a shared portfolio scoring contract

Introduce a common evaluation function so every solver returns objective values
on the same semantic scale. This is the highest-priority fix because the whole
selection dataset depends on it.

### 2. Introduce a richer canonical instance representation

Move beyond `InstanceSummary` for solver-facing work. Keep the summary for
inspection, but add a structured instance model that carries the constraint
information solvers and features actually need.

### 3. Expand solver semantics to use real constraint information

Upgrade CP-SAT and simulated annealing so they consume at least a meaningful
subset of parsed RobinX/ITC2021 constraints. Even partial but consistent
coverage would be much stronger than the current count-only influence.

### 4. Strengthen the feature set with literature-backed descriptors

Add richer structural features: constraint densities, slot pressure, team graph
statistics, hard/soft composition measures, symmetry indicators, and other
features motivated by timetabling literature.

### 5. Tighten input validation and parsing modes

Separate tolerant parsing from strict experiment parsing. Benchmarks and thesis
artifacts should fail fast on malformed XML unless a repaired-input workflow is
explicitly documented.

### 6. Fix post-hoc analysis leakage

Ensure `src/selection/error_analysis.py` excludes `objective_*` columns and any
other benchmark-derived outcome fields from "feature pattern" summaries.

### 7. Upgrade the evaluation protocol

Add repeated seeds, grouped or family-aware splits, and aggregate reporting with
mean and variance. This will strengthen the credibility of any empirical claim.

### 8. Enrich persisted experiment artifacts

Write a run manifest that captures config values, seeds, selected solvers,
dependency versions, and optionally Git commit information alongside benchmark
and selector outputs.

### 9. Rationalize dependencies and packaging

Pin versions, consider a `pyproject.toml`, and remove or defer unused heavy
dependencies until they are actually part of the thesis workflow.

### 10. Expand realistic test coverage

Add richer RobinX-like fixtures, full end-to-end regression tests, evaluation
edge-case tests, and dashboard HTTP tests. The current unit coverage is good,
but the next phase needs more realism-focused tests.

## Overall Assessment

As a software scaffold, the repository is good. As a thesis artifact, it is not
yet ready to support strong claims about algorithm selection for sports
timetabling. The gap is mainly methodological, not stylistic.

That is good news: the architecture is already shaped well enough to support the
next round of scientific strengthening. The most important next move is to make
solver outputs genuinely comparable and structurally grounded in the parsed
problem instances.
