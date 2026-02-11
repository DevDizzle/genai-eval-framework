# GenAI Evaluation Framework

**A comprehensive, extensible framework for evaluating generative AI outputs across safety, accuracy, quality, and brand alignment dimensions.**

Built for teams that need to trust their AI — whether shipping customer-facing content, generating analytical reports, or deploying creative assistants at scale.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Evaluation Pipeline                         │
│                                                                  │
│  ┌──────────┐    ┌──────────────────────────────────────────┐   │
│  │  Model A  │───▶│              Evaluator Suite              │   │
│  └──────────┘    │                                            │   │
│                   │  ┌──────────────┐  ┌──────────────────┐  │   │
│  ┌──────────┐    │  │ Hallucination │  │ Factual Accuracy │  │   │
│  │  Model B  │───▶│  │   Detector    │  │     Scorer       │  │   │
│  └──────────┘    │  └──────────────┘  └──────────────────┘  │   │
│                   │  ┌──────────────┐  ┌──────────────────┐  │   │
│  ┌──────────┐    │  │   Content     │  │  Output Quality  │  │   │
│  │  Source   │───▶│  │   Safety     │  │    Metrics       │  │   │
│  │  Docs     │    │  └──────────────┘  └──────────────────┘  │   │
│  └──────────┘    └───────────────┬──────────────────────────┘   │
│                                   │                               │
│                   ┌───────────────▼──────────────────┐           │
│                   │        A/B Benchmark Engine       │           │
│                   │  • Statistical significance tests │           │
│                   │  • Per-dimension comparison       │           │
│                   │  • Regression detection           │           │
│                   └───────────────┬──────────────────┘           │
│                                   │                               │
│                   ┌───────────────▼──────────────────┐           │
│                   │          Report Generator         │           │
│                   │  • Interactive HTML dashboards    │           │
│                   │  • Structured JSON for CI/CD      │           │
│                   └──────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Metrics Catalog

| Dimension | Metric | Range | Method |
|---|---|---|---|
| **Hallucination** | Entailment Score | 0.0–1.0 | NLI cross-encoder against source docs |
| **Hallucination** | Semantic Drift | 0.0–1.0 | Sentence-embedding cosine similarity |
| **Hallucination** | Unsupported Claim Rate | 0.0–1.0 | Claim extraction + source verification |
| **Factual Accuracy** | Claim Accuracy | 0.0–1.0 | Extracted claims vs. knowledge base |
| **Factual Accuracy** | Numerical Precision | 0.0–1.0 | Numeric claim tolerance matching |
| **Content Safety** | Toxicity Score | 0.0–1.0 | Detoxify multi-label classifier |
| **Content Safety** | Brand Alignment | 0.0–1.0 | Configurable term/topic blocklist |
| **Content Safety** | PII Exposure | count | Regex + NER-based PII detection |
| **Content Safety** | Content Rating | G/PG/PG-13/R | Composite safety classifier |
| **Quality** | Coherence | 1–5 | LLM-as-judge structured evaluation |
| **Quality** | Fluency | 1–5 | LLM-as-judge structured evaluation |
| **Quality** | Relevance | 1–5 | LLM-as-judge structured evaluation |
| **Benchmark** | Win Rate | 0.0–1.0 | Head-to-head comparison across prompts |
| **Benchmark** | Significance | p-value | Paired t-test / Wilcoxon signed-rank |

---

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Run evaluation on sample data
python -m src.benchmark \
  --config configs/eval_config.yaml \
  --data case_studies/financial_signals/sample_data.json \
  --output reports/

# Generate HTML report
python -m src.reporters.html_report --input reports/results.json --output reports/report.html
```

See [GUIDE.md](GUIDE.md) for a detailed walkthrough.

---

## Case Study: Financial Signal Evaluation

The `case_studies/financial_signals/` directory demonstrates the framework evaluating ML-generated trading signal analysis. This showcases:

- **Hallucination detection** on market commentary (did the model fabricate analyst quotes or data?)
- **Factual accuracy** of cited statistics (earnings numbers, price targets, volume data)
- **Content safety** for client-facing distribution (brand-safe language, no PII leakage)
- **A/B comparison** of two model versions generating the same signal reports

See the [case study README](case_studies/financial_signals/README.md) for results and analysis.

---

## Tech Stack

| Component | Technology |
|---|---|
| NLI / Entailment | `cross-encoder/nli-deberta-v3-base` |
| Semantic Similarity | `sentence-transformers/all-MiniLM-L6-v2` |
| Toxicity Detection | `detoxify` (Unitary) |
| PII Detection | Regex patterns + spaCy NER |
| LLM-as-Judge | OpenAI API / local models via config |
| Statistical Testing | `scipy.stats` (t-test, Wilcoxon) |
| Reporting | Jinja2 + Matplotlib |
| Configuration | Pydantic models + YAML |

---

## Extending the Framework

Each evaluator implements a simple interface:

```python
from src.evaluators import BaseEvaluator, EvalResult

class MyCustomEvaluator(BaseEvaluator):
    """Custom evaluator for your domain."""

    def evaluate(self, generated: str, source: str = "", **kwargs) -> EvalResult:
        # Your evaluation logic
        return EvalResult(
            evaluator="my_custom",
            score=0.95,
            details={"explanation": "..."},
            flags=[]
        )
```

Register it in `configs/eval_config.yaml` and it runs automatically in the pipeline.

---

## Project Structure

```
genai-eval-framework/
├── README.md
├── GUIDE.md
├── requirements.txt
├── .gitignore
├── configs/
│   └── eval_config.yaml
├── src/
│   ├── evaluators/
│   │   ├── __init__.py        # Base classes + registry
│   │   ├── hallucination.py   # NLI + semantic similarity
│   │   ├── factual.py         # Claim extraction + verification
│   │   ├── safety.py          # Toxicity, PII, brand, ratings
│   │   └── quality.py         # LLM-as-judge coherence/fluency
│   ├── benchmark.py           # A/B comparison engine
│   └── reporters/
│       ├── html_report.py     # Interactive HTML dashboard
│       └── json_report.py     # Structured JSON output
├── case_studies/
│   └── financial_signals/
│       ├── README.md
│       └── sample_data.json
├── notebooks/
│   └── eval_demo.py           # Jupyter-compatible walkthrough
└── tests/
    └── test_evaluators.py
```

---

## License

MIT
