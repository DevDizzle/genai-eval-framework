# DATA-CONTRACTS.md

## Current Input Shape
Today the benchmark runner consumes dataset-oriented JSON with prompts, sources, and outputs for model A / model B comparisons.

## Recommended Future Contracts

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
    "output": "..."
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
    "prompt_version": "v13"
  }
}
```

### EvalRunResult
```json
{
  "run_id": "uuid",
  "status": "completed",
  "aggregate_score": 0.94,
  "subscores": {
    "factuality": 0.97,
    "safety": 0.99,
    "quality": 0.88
  },
  "flags": [],
  "decision": "pass",
  "reason": "candidate improved aggregate score with no critical regressions"
}
```

## Contract Rules
- Inputs must be validated at ingress.
- Evaluator outputs must have stable field names.
- Promotion decisions must include machine-readable reasons.
- Metadata should be optional but encouraged for auditability.
