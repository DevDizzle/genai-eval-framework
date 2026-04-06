# PRODUCT.md

## Product Thesis
This repo acts as an **evals-as-a-gate for AI systems**: a service that scores candidate outputs, detects regressions, and decides whether prompts, agents, or generated artifacts are promotable.

## Primary Value Proposition
Teams already inspect LLM outputs manually in tools like ChatGPT or Gemini. This system turns that ad hoc review into:
- repeatable evaluation
- baseline comparison
- policy enforcement
- promotion decisions
- scale via API and CI/CD

## Ideal Users
- AI product teams shipping prompt and agent changes
- Internal AI platform teams
- Consulting teams delivering LLM systems to clients
- Structured-output / document-intelligence teams

## Core Use Cases
1. Candidate vs baseline evaluation
2. Golden-set benchmark runs via CI/CD
3. Policy checks for generated artifacts
4. Regression prevention in CI/CD
5. Human-review fallback for borderline runs

## Current Features
- Containerized FastAPI service for evaluation runs
- Interactive UI demo served natively
- Stable eval-run contract
- Baseline vs candidate comparison (regression detection)
- Promotion decision output (`pass`, `fail`, `human_review`)
- Deterministic + judge-based evaluators (using Gemini)
- Firestore persistence for run history with version metadata

## Future Directions
- Hosted evaluation API for multi-tenant usage
- Policy packs by domain
- BigQuery-backed run history and dashboarding
- Webhooks / GitHub checks / deployment gates native integration
