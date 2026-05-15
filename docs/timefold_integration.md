# Timefold Integration

This repository integrates Timefold as an external solver process.
The Python project does not embed a JVM or ship a bundled Timefold model.
Instead, `src/solvers/timefold_adapter.py` converts parsed instances into a
normalized round-robin JSON exchange format, while
`src/solvers/timefold_solver.py` handles subprocess execution and maps the
returned solution back to the shared `SolverResult` format.

Example payloads are included in `data/timefold_examples/`.

## What the Python side expects

Register the solver under the normal benchmark portfolio with the registry name
`timefold`.

Example benchmark config:

```yaml
solvers:
  selected:
    - random_baseline
    - cpsat_solver
    - simulated_annealing_solver
    - timefold
  settings:
    timefold:
      executable_path: C:/tools/timefold-round-robin-adapter.exe
      time_limit_seconds: 60
      command_arguments: []
```

`solvers.settings.timefold.time_limit_seconds` overrides the generic benchmark
time limit for the external Timefold command only. If it is omitted, the solver
uses `run.time_limit_seconds`.

## CLI contract

The configured executable is called with these arguments:

```text
<executable> [command_arguments...] --input <input.json> --output <output.json> --time-limit-seconds <seconds> --random-seed <seed>
```

The Python wrapper always provides `--input`, `--output`,
`--time-limit-seconds`, and `--random-seed`.

## Input JSON

The exported payload uses this schema:

```json
{
  "schema": "timefold_round_robin_v1",
  "config": {
    "run": {
      "name": "InstanceName",
      "timeLimitSeconds": 60,
      "randomSeed": 42
    }
  },
  "modelInput": {
    "instanceName": "InstanceName",
    "roundRobinMode": "single",
    "teams": [
      {"id": "T1", "name": "Team 1", "index": 0}
    ],
    "slots": [
      {"id": "S1", "name": "Round 1", "index": 0}
    ],
    "matches": [
      {
        "id": "M1",
        "homeTeamId": "T1",
        "awayTeamId": "T2",
        "homeTeamName": "Team 1",
        "awayTeamName": "Team 2",
        "leg": 1
      }
    ],
    "constraints": [
      {"family": "Capacity"}
    ],
    "metadata": {
      "requestedSlotCount": 3,
      "minimumRequiredSlots": 3,
      "sourcePath": "data/raw/real/example.xml",
      "parserNotes": []
    }
  }
}
```

For backward compatibility, the exported payload currently also includes a
duplicate `meetings` array with the same contents as `matches`.

The Python side only assumes a compact round-robin representation:

- teams
- slots
- required matches
- declared constraint families as metadata

The external adapter is free to translate that payload into any internal
Timefold model it wants.

## Current limitations

The adapter is intentionally conservative.

Ignored:

- instance-specific RobinX / ITC2021 capacity, break, venue, travel, fairness,
  and sequencing constraints
- soft-constraint penalty structures from the original formulation

Approximated:

- round-robin matches are inferred from the parsed team set and round-robin mode
- slot meaning is reduced to stable round labels and indices
- declared constraint families are exported for traceability, but not enforced
  by the adapter itself

## Accepted output formats

The wrapper accepts either JSON output or a small line-based text format.

Preferred JSON output:

```json
{
  "status": "SOLVED",
  "feasible": true,
  "objectiveValue": 3.0,
  "runtimeSeconds": 1.25,
  "schedule": [
    {"matchId": "M1", "slotId": "S1"}
  ],
  "metadata": {
    "score": "0hard/0soft"
  }
}
```

Accepted text output:

```text
status=SOLVED
feasible=true
objective_value=3
runtime_seconds=1.25
assignment match_id=M1 slot_id=S1
```

For feasible results, the Python wrapper validates that:

- every required match is assigned exactly once
- all referenced matches and slots are known
- no team plays twice in the same slot

If `objectiveValue` is missing for a feasible result, the wrapper derives it as
the number of used slots.

## Failure handling

The wrapper converts common external failures into clean benchmark rows instead
of crashing the whole batch:

- `NOT_CONFIGURED`: no executable path was provided
- `TIMEOUT`: the subprocess exceeded the configured time limit
- `EXECUTION_ERROR`: the executable could not be started
- `INVALID_OUTPUT`: no parseable output was produced
- `INVALID_SOLUTION`: the adapter returned an inconsistent schedule
- `UNSUPPORTED_INSTANCE`: the adapter explicitly marked the instance unsupported

Each failure stores the error string inside `SolverResult.metadata["error"]`, so
the benchmark CSV also gets a readable `error_message`.

## Benchmark integration

Once `timefold` is listed in `solvers.selected`, it appears in the benchmark
pipeline like any other solver:

```bash
python -m src.experiments.run_benchmarks --config configs/benchmark_config.yaml
```

Successful runs write:

- `solver_registry_name = "timefold"`
- `solver_name = "timefold"`

The external adapter remains intentionally decoupled from the Python repo, so
you can iterate on the Timefold model independently without changing the
benchmark pipeline interface.
