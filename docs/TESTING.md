# TESTING.md

## Testing Goals
- Protect evaluator correctness.
- Prevent regressions in benchmark aggregation.
- Ensure promotion decisions remain stable and explainable.
- Verify docs and commands reflect actual project setup.

## Test Layers
1. **Unit tests**
   - evaluator logic
   - threshold handling
   - score aggregation
2. **Golden tests**
   - stable sample datasets with expected pass/fail outcomes
3. **Contract tests**
   - request/response schema validation for future API layer
4. **Smoke tests**
   - benchmark run on sample case study

## Default Commands
```bash
uv run pytest -v
uv run python -m src.benchmark --config configs/eval_config.yaml --data case_studies/financial_signals/sample_data.json --output reports/
```

## Quality Gate Direction
Future acceptance checks should include:
- no critical evaluator failures
- aggregate score threshold met
- no regression on blocker dimensions
- deterministic policy checks pass before judge-only metrics can promote
