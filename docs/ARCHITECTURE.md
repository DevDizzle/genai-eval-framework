# ARCHITECTURE.md

## System Boundary
This project acts as an evaluation gate service. It owns the evaluation pipeline, orchestration, evaluator contracts, reporting artifacts, and API contracts for evaluation-as-a-gate. It does not own model serving, prompt hosting, or external application orchestration.

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
1. **Contracts / Config Layer**
   - Pydantic models for strict API validation
   - YAML / JSON config loading
2. **API & Orchestration Layer**
   - FastAPI service endpoint (`POST /eval/run`)
   - Evaluation suite composition and execution
   - Decision Engine for promotion logic (pass, fail, human_review)
3. **Evaluator Layer**
   - Deterministic checks: hallucination, factuality, safety
   - Model-based judges: quality evaluator using Gemini
4. **Adapters / Integrations**
   - Gemini judge adapters (`google-genai`)
   - Persistence adapters (Google Cloud Firestore)
5. **Infrastructure**
   - Dockerized for Cloud Run deployment
   - Secret Manager for API keys
   - Application Default Credentials (ADC) for Firestore

Dependencies should point inward toward contracts and orchestration.

## Core Data Flow
1. API receives a request with task inputs, sources, candidate outputs, and optional baseline scores.
2. Load eval configuration.
3. Run deterministic evaluators first.
4. Run model-based judge evaluators only where required.
5. Aggregate metric scores and flags.
6. Decision Engine computes comparison deltas and the promotion decision.
7. Return JSON API response artifacts.
8. Persist the run asynchronously to Firestore (redacting full text payloads by default).

## Integration Boundaries
- Input payloads: API requests via REST (`POST /eval/run`).
- Provider APIs: Gemini API via the `google-genai` SDK using Developer API keys (`GEMINI_API_KEY`).
- Storage: Google Cloud Firestore using Application Default Credentials (ADC) for evaluation runs and gating metadata.
- Deployment target: Cloud Run with secrets in Secret Manager.

## Architectural Invariants
- Evaluator results must be machine-readable.
- Deterministic checks should precede LLM-as-judge logic where possible.
- Promotion decisions must be explainable by sub-scores and flags.
- Provider-specific code must not leak across the whole codebase.
- Config and request boundaries must be validated at ingress using Pydantic.
- Version metadata (`suite_version`, `prompt_version`, etc.) must be coupled with evaluation runs to track drift.
- Full text payloads (inputs/outputs) are explicitly redacted in persistence unless overridden by the client.

## Current Gaps
- Advanced Request Authentication / Authorization is missing.
- Packaging has transitioned to `pyproject.toml` + `uv`.
- Full observability metrics not yet exported to BigQuery.
