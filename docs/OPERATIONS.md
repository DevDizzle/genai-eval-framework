# OPERATIONS.md

## Local Development
Preferred setup:
```bash
uv sync
uv run pytest -v

# Required for Firestore persistence (ADC)
gcloud auth application-default login
export FIRESTORE_PROJECT_ID="your-gcp-project-id"

# Required for Gemini judge
export GEMINI_API_KEY="AIza..."

# Start local server
uv run uvicorn src.api:app --reload --port 8080
```

## Dependency Management
- Use `uv add <package>` for new dependencies.
- Use `uv sync` to realize the locked environment.
- Keep `pyproject.toml` as the source of truth.
- `requirements.txt` may remain temporarily for compatibility, but it should not be the primary workflow.

## Deployment Direction
This repo targets:
- Cloud Run for stateless API execution
- Firestore for evaluation run persistence
- Secret Manager for `GEMINI_API_KEY` (if deploying via CI/CD, though Cloud Run env vars work for demo)
- Artifact Registry for images
- optional BigQuery for historical evaluation runs (exported from Firestore)

## Runtime Modes
- **Gemini Judge:** Operates strictly in Developer API mode using `google-genai`. It requires a valid `GEMINI_API_KEY` environment variable. It does *not* use Vertex AI ADC.
- **Firestore Persistence:** Requires Google Cloud ADC. It operates smoothly via local `gcloud auth application-default login` or native Cloud Run Service Account identities.

## Observability Direction
Future production deployment should capture:
- run counts
- latency by evaluator
- provider error rate
- pass/fail/human-review ratios
- regression counts by suite and metric
