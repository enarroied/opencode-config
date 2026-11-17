---
name: tdd-coding
description: Test-first coding for Python behaviour changes. Skip for notebooks, scratch scripts, anything the user calls experimental.
---

# TDD coding

## Skip skill when

- The file is a notebook (`.ipynb`, `marimo`, or Jupyter-style cells).
- The user says "experiment", "spike", "prototype", "scratch", or "just try".
- The task is a config, docs, or formatting change with no behaviour.

## Cycle

1. **Red:** write one failing test for one behaviour. Run it and confirm it fails
   for the expected reason, not an import error or typo.
2. **Green:** write the smallest code that passes. Nothing extra.
3. **Refactor:** with tests green, remove duplication and improve names.

Repeat per behaviour. Never write several tests before the first implementation.

## Principles

- **Single responsibility:** if describing it needs "and", split it.
- **Dependency inversion:** domain depends on ports; I/O lives in adapters.
- **DRY:** merge duplication once the same rule appears twice, not on first sight.
- **Simplicity:** do not add interfaces or abstractions for requirements that don't exist yet.

## Conventions

- Layers: domain logic in `domain/`, use cases in `application/`, I/O in `adapters/`.
- Raise specific exceptions. Don't return `None` to signal failure.
- Comments explain why, never what.
- Name magic numbers where they are defined.

## Stop and ask

- The test is hard to write. The design is probably wrong.
- The change needs a new dependency.
- The requirement is ambiguous.
