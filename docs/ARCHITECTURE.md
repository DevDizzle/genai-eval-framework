# ARCHITECTURE.md

## System Boundary
This project owns the evaluation pipeline, benchmark orchestration, evaluator contracts, reporting artifacts, and future API contracts for evaluation-as-a-gate. It does not yet own model serving, prompt hosting, or external application orchestration.

## Goals
- Evaluate generated outputs against sources, references, and policy rules.
- Compare baseline and candidate systems to detect regressions.
- Produce machine-readable promotion decisions for CI/CD and agent workflows.
- Stay compatible with Gemini / Vertex / GCP-oriented deployment patterns.

## Non-Goals
- General workflow automation for every agent platform.
- Full-featured experiment tracking across all model vendors.
- Human labeling platform.

## Architectural Shape
Recommended layers and dependency direction:
1. **Contracts / Config**
   - Pydantic models
   - YAML / JSON config loading
2. **Application / Orchestration**
   - benchmark runner
   - evaluation suite composition
   - score aggregation
   - promotion decision logic
3. **Evaluator Layer**
   - hallucination
   - factuality
   - safety
   - quality / judge evaluators
   - future policy packs
4. **Adapters / Integrations**
   - Gemini / Vertex judge adapters
   - report renderers
   - future HTTP API / storage adapters
5. **Infrastructure**
   - local file outputs now
   - future Cloud Run + Secret Manager + BigQuery / GCS

Dependencies should point inward toward contracts and orchestration.

## Core Data Flow
1. Load eval configuration.
2. Load task inputs, sources, candidate outputs, and optional baselines.
3. Run deterministic evaluators first.
4. Run model-based judge evaluators only where required.
5. Aggregate metric scores and flags.
6. Compute comparison deltas and promotion decision.
7. Emit JSON / HTML / future API response artifacts.

## Integration Boundaries
- Input datasets: local JSON today, future API payloads.
- Provider APIs: Gemini API via the `google-genai` SDK using Developer API keys (`GEMINI_API_KEY`).
- Storage: Google Cloud Firestore using Application Default Credentials (ADC) for evaluation runs and gating metadata.
- Deployment target: Cloud Run with secrets in Secret Manager.

## Architectural Invariants
- Evaluator results must be machine-readable.
- Deterministic checks should precede LLM-as-judge logic where possible.
- Promotion decisions must be explainable by sub-scores and flags.
- Provider-specific code must not leak across the whole codebase.
- Config and request boundaries must be validated at ingress.
- Version metadata (`suite_version`, `prompt_version`, etc.) must be coupled with evaluation runs to track drift.
- Full text payloads (inputs/outputs) are explicitly redacted in persistence unless overridden by the client.

## Current Gaps
- No formal API service layer yet.
- No stable request/response schema for external consumers.
- Packaging is transitioning from `requirements.txt`-only to `pyproject.toml` + `uv`.
- Deployment and observability are not yet systematized.
