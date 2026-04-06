# DATA-CONTRACTS.md

## Current Input Shape
The service exposes a FastAPI endpoint `POST /eval/run` that enforces strict Pydantic contracts.

### EvalRunRequest
```json
{
  "suite_id": "default-quality-gate",
  "task_type": "summary",
  "input": {
    "prompt": "...",
    "source": "..."
  },
  "candidate": {
    "id": "agent-v13",
    "output": "..."
  },
  "baseline": {
    "id": "agent-v12",
    "output": "...",
    "aggregate_score": 0.82
  },
  "reference": {
    "gold_output": "...",
    "rubric": {
      "requires_citations": true,
      "must_use_uv": true
    }
  },
  "thresholds": {
    "min_score": 0.92,
    "block_on_flags": ["hallucination", "policy_violation"]
  },
  "metadata": {
    "project": "genai-eval-framework",
    "prompt_version": "v13",
    "suite_version": "1.0",
    "commit_sha": "abc1234"
  },
  "store_full_payloads": false
}
```

### EvalRunResult
```json
{
  "run_id": "uuid",
  "status": "completed",
  "aggregate_score": 0.94,
  "sub_scores": {
    "factuality": 0.97,
    "safety": 0.99,
    "quality": 0.88
  },
  "flags": [],
  "decision": "pass",
  "reason": "Candidate meets or exceeds baseline aggregate score with no critical regressions",
  "evaluator_details": {}
}
```

## Contract Rules
- Inputs must be validated at ingress using Pydantic.
- Evaluator outputs must have stable field names.
- Promotion decisions must include machine-readable reasons.
- Metadata is optional but strongly encouraged for auditability and apples-to-apples baseline comparisons.
- By default, `store_full_payloads` is false to prevent persisting sensitive prompts or outputs to the database.
