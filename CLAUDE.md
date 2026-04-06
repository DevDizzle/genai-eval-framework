# CLAUDE.md - GenAI Evaluation Control Plane

## 1. Project Overview & Vision
You are the Lead Developer. I am the Product Manager. We are transforming the `genai-eval-framework` (a local FastAPI evaluation gate) into the **Evaluation Control Plane**, a B2B SaaS web application. It empowers non-technical stakeholders (Legal, Risk, Product) to govern AI agents using natural language rules, manage golden datasets, and review borderline outputs through a "Human-in-the-Loop" UI.

## 2. Tech Stack (The Google Stack)
We are strictly optimizing for the Google Cloud ecosystem:
- **Backend/API:** Python (3.11+), FastAPI (existing codebase in `src/`), managed via `uv`.
- **Frontend:** Next.js (React) with Tailwind CSS / shadcn (to be scaffolded).
- **Database:** Google Cloud Firestore.
- **LLM / Judge:** Gemini Models via the new `google-genai` SDK.
- **Deployment:** Google Cloud Run.

## 3. Architecture & Pointers
- `src/`: Existing Python backend (API, evaluators, decision engine). Do not break existing deterministic logic.
- `docs/`: Technical data contracts and current architecture.
- `ENHANCED_VISION.md`: **MUST READ.** The product vision, core features, and roadmap.
- `STRATEGIC_MARKET_ANALYSIS.md`: Market context and competitive moats (for understanding the "why").

## 4. Developer Tools & Skills (Crucial)
You have access to advanced agent skills and MCP tools. **Use them aggressively before writing code:**
- **MCP Tool:** Use `google-developer-knowledge` to search for up-to-date documentation on Firestore, Cloud Run, Vertex AI, and the Gemini API.
- **Skills:** Activate `gemini-api-dev` and `gemini-interactions-api` for the absolute latest best practices when writing LLM interaction code.
- **Skills:** Activate `adk-scaffold` and `adk-deploy-guide` as we structure the agentic backend and prepare for GCP deployment.

## 5. Coding Rules & Gotchas
- **Deterministic Translation:** When building the "Natural Language Rule Builder", you must translate user text into deterministic, auditable code (e.g., Regex, strict JSON schemas). Do not rely on probabilistic LLM interpretation at runtime for compliance rules.
- **Security:** NEVER commit API keys (e.g., `GEMINI_API_KEY`) or service account JSONs. Assume they are passed via Secret Manager or Cloud Run env variables.
- **Persistence:** All Firestore writes involving complex or nested data should be sanitized. Follow the current paradigm: do NOT persist full text payloads of Prompts/Outputs by default.
- **Statelessness:** Ensure FastAPI routes and the Next.js backend remain strictly stateless for Cloud Run horizontal scaling.

## 6. Common Commands
- **Backend Test:** `uv run pytest tests/ -v`
- **Backend Dev:** `uv run uvicorn src.api:app --reload --port 8080`
- **Dependencies:** `uv add <package>` and `uv sync`
- **Frontend Dev:** `npm run dev` (to be used once the Next.js app is scaffolded)
