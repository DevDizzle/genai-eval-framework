# Case Study: Financial Signal Evaluation

## Overview

This case study demonstrates the GenAI Evaluation Framework applied to
**ML-generated trading signal reports** — a domain where accuracy, safety,
and hallucination detection are critical.

Two model versions generate market analysis text from the same structured
signal data. The framework evaluates both on:

| Dimension | What We're Checking |
|---|---|
| **Hallucination** | Did the model fabricate analyst quotes, data points, or events? |
| **Factual Accuracy** | Are cited statistics (earnings, volume, price targets) correct? |
| **Content Safety** | Is the language appropriate for client distribution? Any PII leakage? |
| **Quality** | Is the analysis coherent, fluent, and relevant to the signal? |

## Sample Data

`sample_data.json` contains 5 prompts with outputs from two model versions:

- **Model A** (`signal-gen-v1.2`): Baseline production model
- **Model B** (`signal-gen-v2.0`): Upgraded model with retrieval augmentation

Each output is a market analysis paragraph generated from structured signal
data. The source documents contain the ground-truth data points.

## Expected Results

Model B (v2.0) should score higher on hallucination and factual accuracy
due to its retrieval-augmented architecture, while both models should
score similarly on safety and quality.

## Running

```bash
python -m src.benchmark \
  --config configs/eval_config.yaml \
  --data case_studies/financial_signals/sample_data.json \
  --output reports/financial_signals/
```
