# Solver Capabilities

This note states the implemented scope of the solver portfolio used in the
thesis experiments. It is intentionally conservative: a solver is described as
supporting only the behavior implemented in this repository or, for Timefold,
the behavior made explicit by the configured external executable.

The per-instance real-data compatibility artifact is
`data/processed/real_pipeline_current/solver_compatibility_matrix.csv`. The
coverage-aware report artifacts are written under `data/results/reports/`.
The same role labels are encoded in `src/solvers/registry.py` and surfaced in
the thesis dashboard, so UI tables do not imply that every portfolio member is
a full RobinX / ITC2021 solver.

## Capability Summary

| Solver | Intended role | Round-robin scope | Constraint handling | Current maturity |
| --- | --- | --- | --- | --- |
| `random_baseline` | Reproducible diagnostic control baseline | Does not construct a schedule | No RobinX / ITC2021 constraints are enforced | Diagnostic only; not a scheduling method |
| `cpsat_solver` | Main compact optimization baseline | Single and double round robin, with explicit home/away legs | Enforces meeting assignment and at-most-one-match-per-team-per-slot; records but does not enforce parsed instance-specific constraint families | Useful structural baseline; partial on constrained real instances |
| `simulated_annealing_solver` | Lightweight heuristic baseline | Simplified single round robin only | Penalizes team-per-slot conflicts and slot usage; does not directly enforce RobinX / ITC2021 constraints | Exploratory heuristic; not an exact solver |
| `timefold` | External solver integration point | Python adapter exports single and double round-robin data | Declared constraints are exported as metadata; enforcement depends on the external Timefold model | Not configured unless an executable path is supplied |

## `random_baseline`

The random baseline produces a deterministic synthetic score from instance
counts and a fixed seed. It exists to exercise parsing, feature extraction,
benchmark export, selector training, and reporting code.

- Supported round-robin scope: none in the scheduling sense; the solver does
  not construct or validate a timetable.
- Supported constraint families: none.
- Unsupported constraint families: all RobinX / ITC2021 hard and soft
  constraint families.
- Benchmark interpretation: rows are marked `partially_supported` with
  `partially_modeled_run`; objectives are deterministic diagnostic values.
- Maturity level: pipeline-control baseline only.

## `cpsat_solver`

The CP-SAT solver is the main optimization baseline. It builds a compact
round-robin model with one required meeting per pair or per leg and prevents a
team from playing more than once in the same slot. Its objective minimizes the
number of used slots, so lower values are better.

- Supported round-robin scope: single round robin and double round robin when
  the parser metadata identifies the instance as `single` or `double`.
- Supported structural constraints: meeting assignment, home/away leg
  representation for double round robin, and team availability per slot.
- Unsupported RobinX / ITC2021 families: capacity, break, home-away pattern,
  venue, travel, fairness, sequence, and soft-penalty constraints.
- Benchmark interpretation: unconstrained structural instances may be marked
  `supported`; instances with parsed constraint families are marked
  `partially_supported` because those families are recorded but not enforced.
- Maturity level: usable compact baseline, not a full competition model.

## `simulated_annealing_solver`

The simulated annealing solver is a lightweight heuristic for simplified
single-round-robin scheduling. It represents one unordered match per team pair
and searches over slot assignments.

- Supported round-robin scope: simplified single round robin.
- Unsupported round-robin scope: double round robin.
- Supported constraint handling: penalty-based treatment of team-per-slot
  conflicts and used slots.
- Unsupported RobinX / ITC2021 families: explicit home/away orientation,
  capacity, break, venue, travel, fairness, sequence, and soft penalties.
- Benchmark interpretation: double-round-robin instances are
  `unsupported`; constrained single-round-robin instances are partial because
  parsed constraint families are not directly modeled.
- Maturity level: simple heuristic baseline for comparison and robustness
  checks.

## `timefold`

The Timefold solver entry is an external subprocess adapter. The Python
repository writes a JSON input file, calls the configured executable, and reads
the JSON output. The repository does not bundle a JVM runtime, build a Timefold
project, or guarantee the external model's constraint semantics.

- Supported round-robin scope: single and double round-robin structures can be
  exported by the Python adapter.
- Supported constraint handling in Python: declared constraint families are
  exported as metadata.
- Unsupported in Python: direct enforcement of capacity, break, venue, travel,
  fairness, sequence, and soft-penalty constraints.
- Configuration status: without an executable path the solver is
  `not_configured`; this is a safe benchmark outcome rather than a pipeline
  failure.
- Benchmark interpretation: configured runs are `supported` only when the
  instance has no declared constraint families; constrained instances are
  `partially_supported` unless the external model is separately documented.
- Maturity level: integration hook for an external model, not an embedded
  solver implementation.

## Thesis Use

The portfolio should be described as a baseline solver portfolio for algorithm
selection experiments, not as a complete RobinX / ITC2021 competition solver
set. Results are most meaningful when performance, feasible coverage, valid
objective coverage, and support status are reported together. The generated
reports in `data/results/reports/` follow this convention.

No current registry entry should be described as a fully complete ITC2021
competition solver. The safest wording is:

- `random_baseline`: diagnostic baseline.
- `cpsat_solver`: compact optimization baseline with partial constraint scope.
- `simulated_annealing_solver`: simplified heuristic baseline.
- `timefold`: external integration point whose maturity depends on the
  configured external executable.
