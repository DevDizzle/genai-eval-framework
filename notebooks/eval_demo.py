# %% [markdown]
# # GenAI Evaluation Framework — Demo Walkthrough
#
# This notebook demonstrates the full evaluation pipeline:
# 1. Load sample model outputs
# 2. Run individual evaluators
# 3. Run the A/B benchmark comparison
# 4. Generate reports
#
# **Requirements:** `pip install -r requirements.txt`

# %% Setup
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# %% [markdown]
# ## 1. Load Sample Data
#
# We'll use the financial signals case study, which compares two model
# versions generating market analysis from structured signal data.

# %%
data_path = project_root / "case_studies" / "financial_signals" / "sample_data.json"
with open(data_path) as f:
    sample_data = json.load(f)

print(f"Prompts: {len(sample_data['prompts'])}")
print(f"Model A: {sample_data['model_a']['id']}")
print(f"Model B: {sample_data['model_b']['id']}")
print(f"\nFirst prompt (truncated):\n{sample_data['prompts'][0][:120]}...")

# %% [markdown]
# ## 2. Run Individual Evaluators
#
# Let's test each evaluator on a single sample before running the full
# benchmark.

# %%
# Pick sample index 0 (AAPL)
idx = 0
prompt = sample_data["prompts"][idx]
source = sample_data["sources"][idx]
gen_a = sample_data["model_a"]["outputs"][idx]["text"]
gen_b = sample_data["model_b"]["outputs"][idx]["text"]

print("=" * 60)
print("PROMPT:")
print(prompt[:200])
print("\nMODEL A OUTPUT (first 200 chars):")
print(gen_a[:200])
print("\nMODEL B OUTPUT (first 200 chars):")
print(gen_b[:200])

# %% [markdown]
# ### 2a. Hallucination Detection

# %%
from src.evaluators.hallucination import HallucinationEvaluator

hall_eval = HallucinationEvaluator(config={
    "nli_model": "cross-encoder/nli-deberta-v3-base",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
})

print("Evaluating Model A for hallucinations...")
hall_a = hall_eval(generated=gen_a, source=source, prompt=prompt)
print(f"  Score: {hall_a.score:.4f}")
print(f"  Entailment: {hall_a.sub_scores.get('entailment', 'N/A')}")
print(f"  Similarity: {hall_a.sub_scores.get('semantic_similarity', 'N/A')}")
print(f"  Flags: {len(hall_a.flags)}")

print("\nEvaluating Model B for hallucinations...")
hall_b = hall_eval(generated=gen_b, source=source, prompt=prompt)
print(f"  Score: {hall_b.score:.4f}")
print(f"  Entailment: {hall_b.sub_scores.get('entailment', 'N/A')}")
print(f"  Similarity: {hall_b.sub_scores.get('semantic_similarity', 'N/A')}")
print(f"  Flags: {len(hall_b.flags)}")

# %% [markdown]
# ### 2b. Factual Accuracy

# %%
from src.evaluators.factual import FactualAccuracyEvaluator

fact_eval = FactualAccuracyEvaluator()

print("Evaluating Model A for factual accuracy...")
fact_a = fact_eval(generated=gen_a, source=source, prompt=prompt)
print(f"  Score: {fact_a.score:.4f}")
print(f"  Total claims: {fact_a.details.get('total_claims', 0)}")
print(f"  Verified: {fact_a.details.get('verified_claims', 0)}")
print(f"  Unverified: {fact_a.details.get('unverified_claims', 0)}")

print("\nEvaluating Model B for factual accuracy...")
fact_b = fact_eval(generated=gen_b, source=source, prompt=prompt)
print(f"  Score: {fact_b.score:.4f}")
print(f"  Total claims: {fact_b.details.get('total_claims', 0)}")
print(f"  Verified: {fact_b.details.get('verified_claims', 0)}")

# %% [markdown]
# ### 2c. Content Safety

# %%
from src.evaluators.safety import ContentSafetyEvaluator

safety_eval = ContentSafetyEvaluator(config={
    "toxicity_threshold": 0.5,
    "forbidden_terms": ["kill", "murder", "porn"],
    "competitor_names": [],
})

print("Evaluating Model A for content safety...")
safety_a = safety_eval(generated=gen_a, source=source, prompt=prompt)
print(f"  Score: {safety_a.score:.4f}")
print(f"  Content Rating: {safety_a.details.get('content_rating')}")
print(f"  PII found: {safety_a.details.get('pii_count', 0)}")
print(f"  Flags: {len(safety_a.flags)}")

print("\nEvaluating Model B for content safety...")
safety_b = safety_eval(generated=gen_b, source=source, prompt=prompt)
print(f"  Score: {safety_b.score:.4f}")
print(f"  Content Rating: {safety_b.details.get('content_rating')}")

# %% [markdown]
# ### 2d. Output Quality

# %%
from src.evaluators.quality import QualityEvaluator

# Using heuristic mode (no API key needed for demo)
quality_eval = QualityEvaluator(config={"use_heuristic": True})

print("Evaluating Model A quality...")
qual_a = quality_eval(generated=gen_a, source=source, prompt=prompt)
print(f"  Composite: {qual_a.score:.4f}")
print(f"  Coherence: {qual_a.details.get('coherence')}/5")
print(f"  Fluency: {qual_a.details.get('fluency')}/5")
print(f"  Relevance: {qual_a.details.get('relevance')}/5")
print(f"  Method: {qual_a.details.get('method')}")

print("\nEvaluating Model B quality...")
qual_b = quality_eval(generated=gen_b, source=source, prompt=prompt)
print(f"  Composite: {qual_b.score:.4f}")
print(f"  Coherence: {qual_b.details.get('coherence')}/5")
print(f"  Fluency: {qual_b.details.get('fluency')}/5")
print(f"  Relevance: {qual_b.details.get('relevance')}/5")

# %% [markdown]
# ## 3. Full A/B Benchmark
#
# Now let's run the complete benchmark across all samples and evaluators.

# %%
from src.benchmark import BenchmarkRunner, load_sample_data, load_config

config_path = project_root / "configs" / "eval_config.yaml"
config = load_config(str(config_path))

# Override to use heuristic quality (no API key needed)
config.setdefault("evaluators", {}).setdefault("quality", {})["use_heuristic"] = True

runner = BenchmarkRunner(config)
outputs_a, outputs_b = load_sample_data(str(data_path))

print("Running full benchmark...")
result = runner.run(outputs_a, outputs_b)

print(f"\nOverall winner: {result.overall_winner}")
print(f"\nPer-evaluator results:")
import numpy as np
for ev in result.evaluator_names:
    mean_a = np.mean(result.scores_a[ev])
    mean_b = np.mean(result.scores_b[ev])
    p = result.significance[ev]["p_value"]
    w = result.winner[ev]
    print(f"  {ev:20s}  A={mean_a:.3f}  B={mean_b:.3f}  p={p:.4f}  → {w}")

# %% [markdown]
# ## 4. Generate Reports

# %%
from src.reporters.json_report import generate_json_report
from src.reporters.html_report import generate_html_report

reports_dir = project_root / "reports"
reports_dir.mkdir(exist_ok=True)

result_dict = result.to_dict()

json_path = generate_json_report(result_dict, str(reports_dir / "results.json"))
print(f"JSON report: {json_path}")

html_path = generate_html_report(result_dict, str(reports_dir / "report.html"))
print(f"HTML report: {html_path}")

# %% [markdown]
# ## 5. Inspect Results
#
# Let's look at the detailed results for the first sample.

# %%
print("Sample 0 — Model A detailed results:")
print(json.dumps(result.results_a[0], indent=2, default=str)[:2000])

# %% [markdown]
# ## Next Steps
#
# 1. **Add your own data:** Create a JSON file matching the sample_data format
# 2. **Configure evaluators:** Edit `configs/eval_config.yaml`
# 3. **Add custom evaluators:** Subclass `BaseEvaluator`
# 4. **Enable LLM-as-judge:** Set `OPENAI_API_KEY` and disable heuristic mode
# 5. **Integrate into CI/CD:** Use the JSON report's `ci.passed` field
