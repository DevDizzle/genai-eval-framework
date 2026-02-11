# Step-by-Step Guide

**Estimated time: 4–6 hours** (including understanding the code and customising for your domain)

---

## Step 1: Install Dependencies (15 min)

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

**Note:** The first run will download model weights (~500MB for NLI + embedding models). Subsequent runs use cached weights.

---

## Step 2: Run the Demo Notebook on Sample Data (30 min)

The notebook walks through every evaluator individually, then runs the full A/B benchmark.

```bash
# Option A: Run as a script
python notebooks/eval_demo.py

# Option B: Open in Jupyter (if installed)
pip install jupytext jupyter
jupytext --to notebook notebooks/eval_demo.py
jupyter notebook notebooks/eval_demo.ipynb
```

**What you'll see:**
- Per-sentence hallucination scores with NLI labels
- Claim extraction and verification results
- Toxicity scores, PII detection, content ratings
- Quality scores (heuristic mode — set `OPENAI_API_KEY` for LLM-as-judge)
- A/B comparison with statistical significance tests
- Generated HTML and JSON reports in `reports/`

---

## Step 3: Add Your Own Model Outputs (1–2 hours)

Create a JSON file matching the sample data format:

```json
{
  "prompts": ["Your prompt 1", "Your prompt 2", ...],
  "sources": ["Ground truth 1", "Ground truth 2", ...],
  "model_a": {
    "id": "your-model-v1",
    "outputs": [
      {"text": "Model A output for prompt 1"},
      {"text": "Model A output for prompt 2"}
    ]
  },
  "model_b": {
    "id": "your-model-v2",
    "outputs": [
      {"text": "Model B output for prompt 1"},
      {"text": "Model B output for prompt 2"}
    ]
  }
}
```

Then run:

```bash
python -m src.benchmark \
  --config configs/eval_config.yaml \
  --data path/to/your_data.json \
  --output reports/your_experiment/
```

---

## Step 4: Customise Evaluators for Your Domain (1–2 hours)

### Safety Configuration

Edit `configs/eval_config.yaml` to set brand-specific rules:

```yaml
evaluators:
  content_safety:
    forbidden_terms:
      - "your_forbidden_word"
    forbidden_topics:
      - "your_sensitive_topic"
    competitor_names:
      - "CompetitorBrand"
    toxicity_threshold: 0.3  # stricter threshold
```

### Custom Evaluator

Create a new evaluator in `src/evaluators/`:

```python
from src.evaluators import BaseEvaluator, EvalResult, register

@register
class CharacterConsistencyEvaluator(BaseEvaluator):
    name = "character_consistency"

    def evaluate(self, generated, source="", prompt="", **kwargs):
        # Your evaluation logic here
        return EvalResult(evaluator=self.name, score=0.95, details={...})
```

Import it in `src/evaluators/__init__.py` and it's automatically available.

### LLM-as-Judge Quality

For production-quality scoring, enable the LLM judge:

```bash
export OPENAI_API_KEY="sk-..."
```

Then set `use_heuristic: false` in the config.

---

## Step 5: Generate Report (15 min)

Reports are generated automatically by the benchmark runner. You can also generate them standalone:

```bash
# HTML report with charts
python -m src.reporters.html_report \
  --input reports/results.json \
  --output reports/report.html

# JSON for CI/CD integration
python -m src.reporters.json_report \
  --input reports/results.json \
  --output reports/results_formatted.json
```

The JSON report includes a `ci.passed` field for automated quality gates.

---

## Step 6: Update README (15 min)

After customising the framework:

1. Update the **Tech Stack** table if you added new dependencies
2. Add your custom evaluators to the **Metrics Catalog**
3. Document your case study in `case_studies/`
4. Update the **Architecture** diagram if you modified the pipeline

---

## Tips

- **Start with heuristic quality scoring** — it requires no API keys
- **Run tests** with `pytest tests/ -v` to verify everything works
- **The HTML report** is self-contained — share it as a single file
- **For CI/CD**, use the JSON report's `ci.passed` boolean as a quality gate
- **Scale up** by adding more samples — statistical tests become more powerful with n > 30
