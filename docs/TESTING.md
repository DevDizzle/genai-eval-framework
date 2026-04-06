# TESTING.md

## Testing Goals
- Protect evaluator correctness.
- Prevent regressions in decision engine and aggregation.
- Ensure promotion decisions remain stable and explainable.
- Verify docs and commands reflect actual project setup.

## Test Layers
1. **Unit tests**
   - evaluator logic
   - threshold handling
   - decision engine rules
   - score aggregation
2. **Contract tests**
   - request/response schema validation for the FastAPI layer
3. **Integration tests**
   - api endpoint testing
   - persistence testing (with mock database)

## Default Commands
```bash
uv sync
uv run pytest tests/ -v
```

## Quality Gate Direction
Acceptance checks for the evaluation service itself include:
- no critical evaluator failures
- aggregate score threshold met
- no regression on blocker dimensions
- deterministic policy checks pass before judge-only metrics can promote
