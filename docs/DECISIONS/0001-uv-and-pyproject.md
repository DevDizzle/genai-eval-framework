# 0001 - Adopt uv and pyproject.toml as the default developer workflow

## Status
Accepted

## Context
The repository was initialized with `requirements.txt` and README/GUIDE instructions centered on `pip install -r requirements.txt`. That works, but it is weaker than a modern Python workflow for repeatable local development and future CI/CD.

## Decision
Adopt `uv` and `pyproject.toml` as the default dependency and execution workflow.

## Consequences
- Local setup becomes faster and more reproducible.
- Docs and agent governance should point to `uv sync`, `uv add`, and `uv run ...`.
- `requirements.txt` can remain temporarily for compatibility, but `pyproject.toml` becomes the primary source of truth.
