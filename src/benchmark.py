"""
A/B Benchmark Engine
=====================

Run the same prompts through two models (or model versions), evaluate both
using the full evaluator suite, and produce a statistically rigorous
comparison report.

Usage::

    python -m src.benchmark \\
        --config configs/eval_config.yaml \\
        --data case_studies/financial_signals/sample_data.json \\
        --output reports/
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

from src.evaluators import (
    BaseEvaluator,
    EvalResult,
    available_evaluators,
    get_evaluator,
)
from src.reporters.json_report import generate_json_report
from src.reporters.html_report import generate_html_report


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ModelOutput:
    """A single model output paired with its source / prompt."""
    prompt: str
    generated: str
    source: str = ""
    model_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Full benchmark comparison between two models."""
    model_a: str
    model_b: str
    num_samples: int
    evaluator_names: List[str]
    scores_a: Dict[str, List[float]]  # evaluator -> list of per-sample scores
    scores_b: Dict[str, List[float]]
    results_a: List[Dict[str, Any]]  # full per-sample results
    results_b: List[Dict[str, Any]]
    significance: Dict[str, Dict[str, float]]  # evaluator -> {t_stat, p_value, ...}
    winner: Dict[str, str]  # evaluator -> "model_a" | "model_b" | "tie"
    overall_winner: str
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_a": self.model_a,
            "model_b": self.model_b,
            "num_samples": self.num_samples,
            "evaluators": self.evaluator_names,
            "summary": {
                ev: {
                    "mean_a": round(float(np.mean(self.scores_a[ev])), 4),
                    "mean_b": round(float(np.mean(self.scores_b[ev])), 4),
                    "std_a": round(float(np.std(self.scores_a[ev])), 4),
                    "std_b": round(float(np.std(self.scores_b[ev])), 4),
                    "winner": self.winner[ev],
                    **{k: round(v, 6) for k, v in self.significance[ev].items()},
                }
                for ev in self.evaluator_names
            },
            "overall_winner": self.overall_winner,
            "timestamp": self.timestamp,
            "detailed_results_a": self.results_a,
            "detailed_results_b": self.results_b,
        }


# ---------------------------------------------------------------------------
# Statistical testing
# ---------------------------------------------------------------------------

def compare_scores(
    scores_a: List[float], scores_b: List[float], alpha: float = 0.05
) -> Tuple[Dict[str, float], str]:
    """Run paired statistical tests and determine winner.

    Uses paired t-test for n >= 30, Wilcoxon signed-rank for smaller samples.
    """
    a = np.array(scores_a)
    b = np.array(scores_b)
    diff = a - b

    result: Dict[str, float] = {}

    if len(a) >= 30:
        t_stat, p_value = stats.ttest_rel(a, b)
        result["t_statistic"] = float(t_stat)
        result["p_value"] = float(p_value)
        result["test"] = 0  # 0 = t-test (store as float for JSON)
    else:
        # Wilcoxon requires non-zero differences
        nonzero = diff[diff != 0]
        if len(nonzero) < 2:
            result["p_value"] = 1.0
            result["test"] = 1  # wilcoxon
        else:
            w_stat, p_value = stats.wilcoxon(nonzero)
            result["w_statistic"] = float(w_stat)
            result["p_value"] = float(p_value)
            result["test"] = 1

    result["mean_diff"] = float(np.mean(diff))
    result["effect_size"] = float(
        np.mean(diff) / max(np.std(diff), 1e-10)
    )  # Cohen's d

    # Determine winner
    if result["p_value"] < alpha:
        winner = "model_a" if result["mean_diff"] > 0 else "model_b"
    else:
        winner = "tie"

    return result, winner


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

class BenchmarkRunner:
    """Orchestrates A/B evaluation across all evaluators."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.evaluators: Dict[str, BaseEvaluator] = {}
        self._setup_evaluators()

    def _setup_evaluators(self) -> None:
        """Instantiate evaluators based on config."""
        eval_configs = self.config.get("evaluators", {})
        for name in available_evaluators():
            ev_config = eval_configs.get(name, {})
            if ev_config.get("enabled", True):
                self.evaluators[name] = get_evaluator(name, ev_config)

    def evaluate_sample(
        self, output: ModelOutput
    ) -> Dict[str, EvalResult]:
        """Run all evaluators on a single model output."""
        results = {}
        for name, evaluator in self.evaluators.items():
            try:
                result = evaluator(
                    generated=output.generated,
                    source=output.source,
                    prompt=output.prompt,
                )
                results[name] = result
            except Exception as e:
                results[name] = EvalResult(
                    evaluator=name,
                    score=0.0,
                    details={"error": str(e)},
                )
        return results

    def run(
        self,
        outputs_a: List[ModelOutput],
        outputs_b: List[ModelOutput],
        alpha: float = 0.05,
    ) -> BenchmarkResult:
        """Run full A/B benchmark comparison.

        Args:
            outputs_a: Model A outputs (one per prompt).
            outputs_b: Model B outputs (same prompts, same order).
            alpha: Significance level for statistical tests.

        Returns:
            BenchmarkResult with per-evaluator comparisons.
        """
        assert len(outputs_a) == len(outputs_b), (
            "Model A and B must have the same number of samples."
        )

        model_a_id = outputs_a[0].model_id if outputs_a else "model_a"
        model_b_id = outputs_b[0].model_id if outputs_b else "model_b"
        evaluator_names = list(self.evaluators.keys())

        scores_a: Dict[str, List[float]] = {n: [] for n in evaluator_names}
        scores_b: Dict[str, List[float]] = {n: [] for n in evaluator_names}
        results_a_all: List[Dict[str, Any]] = []
        results_b_all: List[Dict[str, Any]] = []

        for i, (out_a, out_b) in enumerate(zip(outputs_a, outputs_b)):
            print(f"  Evaluating sample {i + 1}/{len(outputs_a)}...", flush=True)

            res_a = self.evaluate_sample(out_a)
            res_b = self.evaluate_sample(out_b)

            sample_a = {"sample_index": i, "prompt": out_a.prompt}
            sample_b = {"sample_index": i, "prompt": out_b.prompt}

            for name in evaluator_names:
                scores_a[name].append(res_a[name].score)
                scores_b[name].append(res_b[name].score)
                sample_a[name] = res_a[name].to_dict()
                sample_b[name] = res_b[name].to_dict()

            results_a_all.append(sample_a)
            results_b_all.append(sample_b)

        # Statistical tests
        significance = {}
        winners = {}
        for name in evaluator_names:
            sig, winner = compare_scores(scores_a[name], scores_b[name], alpha)
            significance[name] = sig
            winners[name] = winner

        # Overall winner: majority vote across evaluators
        a_wins = sum(1 for w in winners.values() if w == "model_a")
        b_wins = sum(1 for w in winners.values() if w == "model_b")
        if a_wins > b_wins:
            overall = model_a_id
        elif b_wins > a_wins:
            overall = model_b_id
        else:
            overall = "tie"

        return BenchmarkResult(
            model_a=model_a_id,
            model_b=model_b_id,
            num_samples=len(outputs_a),
            evaluator_names=evaluator_names,
            scores_a=scores_a,
            scores_b=scores_b,
            results_a=results_a_all,
            results_b=results_b_all,
            significance=significance,
            winner=winners,
            overall_winner=overall,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_sample_data(path: str) -> Tuple[List[ModelOutput], List[ModelOutput]]:
    """Load sample data JSON file.

    Expected format:
    {
        "model_a": {"id": "...", "outputs": [...]},
        "model_b": {"id": "...", "outputs": [...]},
        "prompts": [...],
        "sources": [...]
    }
    """
    with open(path) as f:
        data = json.load(f)

    prompts = data.get("prompts", [])
    sources = data.get("sources", [])

    def _build(model_key: str) -> List[ModelOutput]:
        model_data = data[model_key]
        model_id = model_data.get("id", model_key)
        outputs = model_data["outputs"]
        result = []
        for i, out in enumerate(outputs):
            if isinstance(out, str):
                gen = out
                meta = {}
            else:
                gen = out.get("text", out.get("generated", ""))
                meta = {k: v for k, v in out.items() if k not in ("text", "generated")}
            result.append(
                ModelOutput(
                    prompt=prompts[i] if i < len(prompts) else "",
                    generated=gen,
                    source=sources[i] if i < len(sources) else "",
                    model_id=model_id,
                    metadata=meta,
                )
            )
        return result

    return _build("model_a"), _build("model_b")


def load_config(path: str) -> Dict[str, Any]:
    """Load YAML config file."""
    import yaml

    with open(path) as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="GenAI A/B Benchmark — compare two models across all evaluation dimensions."
    )
    parser.add_argument("--config", required=True, help="Path to eval_config.yaml")
    parser.add_argument("--data", required=True, help="Path to sample data JSON")
    parser.add_argument("--output", default="reports/", help="Output directory")
    parser.add_argument("--alpha", type=float, default=0.05, help="Significance level")
    args = parser.parse_args()

    print("Loading config...", flush=True)
    config = load_config(args.config)

    print("Loading sample data...", flush=True)
    outputs_a, outputs_b = load_sample_data(args.data)
    print(f"  {len(outputs_a)} samples per model", flush=True)

    print("Running benchmark...", flush=True)
    runner = BenchmarkRunner(config)
    result = runner.run(outputs_a, outputs_b, alpha=args.alpha)

    # Generate reports
    os.makedirs(args.output, exist_ok=True)

    json_path = os.path.join(args.output, "results.json")
    generate_json_report(result.to_dict(), json_path)
    print(f"  JSON report: {json_path}", flush=True)

    html_path = os.path.join(args.output, "report.html")
    generate_html_report(result.to_dict(), html_path)
    print(f"  HTML report: {html_path}", flush=True)

    print(f"\n{'='*60}")
    print(f"  Overall winner: {result.overall_winner}")
    print(f"{'='*60}")
    for ev in result.evaluator_names:
        mean_a = np.mean(result.scores_a[ev])
        mean_b = np.mean(result.scores_b[ev])
        p = result.significance[ev]["p_value"]
        w = result.winner[ev]
        print(f"  {ev:20s}  A={mean_a:.3f}  B={mean_b:.3f}  p={p:.4f}  → {w}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
