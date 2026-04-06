# GEMINI.md - Operating Contract for GenAI Eval Framework

This is the single project-context and governance file for Gemini-assisted development in this repository.

## Project Goal
Build and harden a production-oriented evaluation service that acts as a release gate for Gemini- and GCP-based AI systems, preventing regressions across prompts, agents, and generated artifacts.

## Product Direction
This repo should evolve from a local evaluation framework into an API-first evaluation control plane:
- evaluate candidate outputs and agent runs
- compare candidates against baselines and golden sets
- enforce policy / SWE constraints
- produce promotion decisions (`pass`, `fail`, `human_review`)
- integrate with CI/CD and agent workflows

## Preferred Stack
- Python 3.11+
- `uv` for dependency and environment management
- Gemini API / Vertex AI for judge-based and multimodal evaluators when needed
- GCP-first deployment posture (Cloud Run, Secret Manager, BigQuery / GCS as needed)
- Pydantic for contracts and config validation
- pytest for tests

## Mission
Use Gemini to help build a production-grade evaluation service for AI systems on a GCP-first stack. The system should support regression prevention, promotion control, and evaluation-as-a-gate for prompts, agents, and generated artifacts.

## Documentation Pointers (Lazy Loading Context)
Read only what is needed before making meaningful changes:
- System architecture: `docs/ARCHITECTURE.md`
- Product framing and roadmap: `docs/PRODUCT.md`
- Core domain concepts: `docs/DOMAIN.md`
- Data contracts / request-response models: `docs/DATA-CONTRACTS.md`
- Testing and quality gates: `docs/TESTING.md`
- Security / secrets / trust boundaries: `docs/SECURITY.md`
- Operations / local-dev / deployment posture: `docs/OPERATIONS.md`
- Key architecture decisions: `docs/DECISIONS/`

## Non-Negotiables
- Use `uv` for environment and dependency management.
- Keep architecture docs current when behavior or scope changes.
- Prefer typed contracts and explicit thresholds over vague scoring.
- Never add secrets, API keys, or service-account JSON to the repo.
- Do not make framework-level changes without updating tests and relevant docs.

## Required Working Pattern
1. Read this file first.
2. Read only the relevant `docs/*.md` files needed for the task.
3. Make the smallest coherent change that preserves architectural invariants.
4. Run targeted validation (`uv run pytest`, targeted module checks, lint if configured).
5. Update docs if the implementation meaningfully changed.

## Working Rules
- Use `uv`, not `pip install -r requirements.txt`, for default setup and dependency changes.
- Treat evaluation as decision infrastructure, not just analytics.
- Prefer hybrid evaluators: deterministic rules first, model-based judging second.
- New evaluator types must define contracts, thresholds, and failure modes.
- Keep repo guidance in `docs/` and `.gemini/`, not in transient chat context.
- Never commit secrets, provider keys, service-account JSON, or customer evaluation payloads.
- Before marking work done: run tests, validate docs drift, and ensure instructions still match the repo.

## SWE Rules
- Dependency management: `uv sync`, `uv add`, `uv run ...`
- Prefer `pyproject.toml` as the source of truth.
- Preserve clear layer boundaries:
  - contracts/config
  - evaluation orchestration
  - evaluator implementations
  - reporting/adapters
- Put provider-specific logic behind adapters.
- Make evaluator outputs machine-readable and stable.
- Add deterministic checks before LLM-as-judge whenever possible.

## Gemini / GCP Guidance
- Default to the modern Gemini SDKs and current Google guidance; avoid stale client libraries or deprecated examples.
- For Google API / Gemini / Vertex questions, consult the available Google knowledge surfaces before inventing patterns.
- Prefer GCP-native production patterns when adding deployment docs or service architecture.

## Relevant Tools / Skills To Use
When available in the local agent environment, prefer these before guessing:
- MCP: `google-developer-knowledge` for current Google / Gemini / Vertex / GCP docs
- Skill: `gemini-api-dev`
- Skill: `gemini-interactions-api`
- Skill: `vertex-ai-api-dev`
- Skill: `adk-scaffold` when turning this into a fuller agent project
- Skill: `adk-deploy-guide` when documenting or implementing GCP deployment

## Repo-Specific Objectives
This repository should mature toward these capabilities:
- API endpoint for evaluation runs
- baseline vs candidate comparison
- golden dataset and rubric support
- promotion decisions (`pass`, `fail`, `human_review`)
- policy packs (citations, schema, tool-use, SWE conventions)
- CI/CD and agent integration

## Change Acceptance Criteria
A change is only acceptable if:
- contracts are still clear
- tests pass or are updated intentionally
- docs and governance remain aligned
- the change improves reliability, auditability, or promotion control

## Near-Term Priorities
1. Harden project harness and developer governance.
2. Normalize packaging around `uv` + `pyproject.toml`.
3. Add API-oriented contracts for evaluation runs and promotion decisions.
4. Add regression-suite patterns for prompts, agents, and generated artifacts.
5. Prepare a deployable GCP service path once the local framework contracts stabilize.

## Suggested Local Commands
```bash
uv sync
uv run pytest -v
uv run python -m src.benchmark --config configs/eval_config.yaml --data case_studies/financial_signals/sample_data.json --output reports/
```

## When Adding New Features
For any new evaluator, API route, or promotion rule, document:
- purpose
- inputs / outputs
- thresholds
- failure modes
- deterministic vs model-based logic
- security / trust boundary implications
