# PRODUCT.md

## Product Thesis
This repo should evolve into **evals-as-a-gate for AI systems**: a service that scores candidate outputs, detects regressions, and decides whether prompts, agents, or generated artifacts are promotable.

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
2. Golden-set benchmark runs
3. Policy checks for generated artifacts
4. Regression prevention in CI/CD
5. Human-review fallback for borderline runs

## Near-Term V1
- containerized FastAPI service for evaluation runs
- interactive UI demo served natively
- stable eval-run contract
- baseline vs candidate comparison
- promotion decision output
- deterministic + judge-based evaluators (Gemini)
- Firestore persistence for run history

## Future Directions
- hosted evaluation API
- policy packs by domain
- BigQuery-backed run history
- dashboarding
- webhooks / GitHub checks / deployment gates
