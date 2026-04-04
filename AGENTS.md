# AGENTS.md

## Purpose

This repository contains the practical implementation for a master's thesis on sports tournament scheduling algorithm selection based on problem structural characteristics.

The project is expected to:

1. Parse RobinX / ITC2021 sports timetabling instances.
2. Extract structural features from each instance.
3. Implement a small portfolio of scheduling solvers.
4. Run benchmark experiments.
5. Build an algorithm selection dataset.
6. Train and evaluate a selector model.

## Working principles

- Use Python only.
- Keep the code thesis-quality, typed, readable, and modular.
- Do not add unnecessary frameworks or heavy dependencies.
- Prefer small, well-scoped files and straightforward abstractions.
- Add docstrings and comments only where they improve understanding.
- Keep outputs reproducible.
- Do not overengineer.
- When unsure, choose the simpler implementation first.

## Definition of done

For every task:

- Code is created in the correct folder.
- Imports work.
- The code is runnable.
- If relevant, tests are added.
- `README` is updated when behavior changes.

## Coding style

- Prefer clear, typed Python with descriptive names and simple control flow.
- Keep modules focused on one responsibility.
- Favor standard library solutions unless a dependency provides clear value.
- Write functions and classes that are easy to test in isolation.
- Use comments sparingly; prefer readable code over explanatory noise.

## Experimental philosophy

- Start with correct, reproducible baselines before optimizing.
- Keep data processing, feature extraction, solver execution, and evaluation clearly separated.
- Make experimental assumptions explicit in code and configuration.
- Prefer deterministic behavior, fixed seeds, and traceable outputs where possible.
- Add complexity only when it is justified by research value or empirical results.
