# GenAI Evaluation Gate

**Evaluation gate infrastructure for regression prevention, promotion control, and AI release confidence.**

This repository provides a containerized service and demo UI for evaluating AI outputs (prompts, agents, artifacts) against references, baselines, and rigorous policy rules. It transforms ad-hoc LLM testing into a definitive, API-driven gating decision: `pass`, `fail`, or `human_review`.

## Core Features

- **Evaluation API:** FastAPI-based service to receive candidate outputs and return structured gating decisions.
- **Decision Engine:** Configurable promotion logic based on aggregate scores, deterministic blocker flags, and baseline regression thresholds.
- **Extensible Evaluators:** Hallucination, factuality, safety, and quality checks (deterministic + model-based Gemini judges).
- **Demo UI:** A lightweight frontend to interactively demonstrate the evaluation gating workflow and view historical runs.
- **Containerized:** Ready to build and deploy (e.g., to Google Cloud Run).

## Architecture & Runtime Modes

The system operates as a single deployable container exposing a REST API and a lightweight demonstration frontend:

1. **API Layer (`src/api.py`):** FastAPI handles incoming requests (`POST /eval/run`), enforcing strict Pydantic contracts (`src/contracts.py`).
2. **Evaluator Orchestration (`src/benchmark.py`):** Runs the suite of deterministic evaluators and model-based judges (defaulting to `gemini-3-pro-preview`).
   - **Gemini Runtime Mode:** The Quality Judge is strictly implemented to use the **Gemini Developer API mode** (via the `google-genai` SDK) requiring a `GEMINI_API_KEY`. It does NOT assume Vertex AI Application Default Credentials (ADC) for model calls.
3. **Decision Engine (`src/decision_engine.py`):** Takes scores, flags, and thresholds to produce the final promotion decision (`pass`, `fail`, `human_review`).
4. **Persistence Layer (`src/persistence.py`):** Uses Google Cloud Firestore to save runs.
   - **Firestore Runtime Mode:** The Firestore client requires Google Cloud Application Default Credentials (ADC) to authenticate to the GCP project.
   - **Fallback:** Gracefully falls back to an in-memory datastore if GCP/Firestore is not configured.

### Persistence Redaction & Versioning
When saving evaluation runs, you can supply `version_metadata` (e.g. `suite_version`, `prompt_version`, `commit_sha`) in your request to track regressions over time. By default, exact input and output payloads are redacted from the database for security; you must pass `store_full_payloads: true` to persist them.

## Configuration & Environment Variables

To fully utilize the application (including LLM-as-judge and run history):

- `GEMINI_API_KEY`: Required to enable the Gemini judge for quality evaluation. (Developer API).
- `FIRESTORE_PROJECT_ID`: Set this to your GCP project ID to enable Firestore persistence. If omitted, a temporary in-memory database will be used.

## Local Development (uv)

The project uses `uv` for dependency management.

```bash
# Sync dependencies
uv sync

# Run tests
uv run pytest -v

# Authenticate your local environment for Firestore (ADC)
gcloud auth application-default login

# Start the local development server
export FIRESTORE_PROJECT_ID="your-gcp-project-id"
export GEMINI_API_KEY="AIza..."
uv run uvicorn src.api:app --reload --port 8080
```

Once running, navigate to `http://localhost:8080/demo` to access the interactive UI.

## Demo Flow

The included Demo UI (`/demo` or `/`) showcases the core gating capability. It is intentionally self-contained and served directly from the FastAPI application container. 

**Design Sync:** The UI visually mirrors the design tokens of [evanparra.ai](https://evanparra.ai) (including the specific `system-ui` stack, neutral backgrounds, white card surfaces, blue primary accents, and an 8px border radius) so it acts as a cohesive live product demo. It is built using simple HTML/CSS (`src/templates/index.html` and `src/static/style.css`) without requiring a heavyweight JS framework.

1. **Load Example:** The demo ships with a pre-loaded example scenario (summarization task).
2. **Inputs:** Provide the task prompt and source reference.
3. **Candidate vs Baseline:** Enter the accepted baseline output and the new candidate output.
4. **Evaluate:** Clicking "Run Quality Gate" triggers the API.
5. **Results:** See the final decision badge (`PASS`, `FAIL`, or `HUMAN_REVIEW`), subscores, flags, and the raw API response explaining *why* the candidate was accepted or rejected. The evaluator method (e.g., `gemini-3-pro-preview` Judge) is dynamically extracted and displayed.
6. **Recent Runs:** The UI displays recent historical runs fetched from the persistence layer.

## Container Build & Run

To run the application in a production-like containerized environment locally:

```bash
# Build the Docker image
docker build -t genai-eval-gate .

# Run the container (requires passing the credentials via mount for Firestore, or omitting for in-memory)
docker run -p 8080:8080 -e GEMINI_API_KEY=$GEMINI_API_KEY genai-eval-gate
```

## Cloud Run Deployment

To deploy this service directly to Google Cloud Run, execute:

```bash
gcloud run deploy genai-eval-gate \
  --source . \
  --project profitscout-lx6bb \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars FIRESTORE_PROJECT_ID=profitscout-lx6bb \
  --set-env-vars GEMINI_API_KEY="your-gemini-api-key"
```

The service and UI will be available at the provided `.run.app` URL.

## Roadmap: Toward a Hosted Eval Service

To graduate this local gate into a fully hosted, production-grade service:

1. **Auth & Security:** Add API key authentication (e.g., via Google API Gateway or custom middleware) and Secret Manager for LLM judge API keys.
2. **Analytics:** Export Firestore runs to BigQuery to analyze historical regression trends over time.
3. **CI/CD Integration:** Create GitHub Actions / GitLab CI adapters that call `POST /eval/run` during pipeline execution and fail the build on a `fail` decision.
4. **Advanced Policy Packs:** Add domain-specific evaluator suites (e.g., financial analysis, medical summarization).

## License

MIT
