# QUALITY.md

## Quality Philosophy
Quality is not a single scalar score. This project should produce enough evidence to support a release decision.

## Metric Classes
- deterministic policy checks
- factuality / grounding checks
- safety checks
- judge-based quality checks
- comparison deltas against baseline

## Promotion Logic Direction
Default top-level outcomes:
- `pass`
- `fail`
- `human_review`

A high aggregate score is insufficient if blocker rules fail.
