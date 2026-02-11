"""
JSON Report Generator
======================

Produces structured JSON output for programmatic consumption — CI/CD
pipelines, dashboards, and downstream analysis.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def generate_json_report(
    data: Dict[str, Any],
    output_path: str,
    indent: int = 2,
    include_details: bool = True,
) -> str:
    """Generate a structured JSON evaluation report.

    Args:
        data: Benchmark result dict (from BenchmarkResult.to_dict()).
        output_path: Where to write the JSON file.
        indent: JSON indentation level.
        include_details: Whether to include per-sample detailed results.

    Returns:
        The output file path.
    """
    output = {
        "schema_version": "1.0",
        "framework": "genai-eval-framework",
        "model_a": data.get("model_a"),
        "model_b": data.get("model_b"),
        "num_samples": data.get("num_samples"),
        "overall_winner": data.get("overall_winner"),
        "timestamp": data.get("timestamp"),
        "summary": data.get("summary", {}),
    }

    if include_details:
        output["detailed_results_a"] = data.get("detailed_results_a", [])
        output["detailed_results_b"] = data.get("detailed_results_b", [])

    # Compute pass/fail for CI integration
    summary = data.get("summary", {})
    output["ci"] = {
        "passed": all(
            s.get("mean_a", 0) >= 0.5 or s.get("mean_b", 0) >= 0.5
            for s in summary.values()
        ),
        "evaluator_status": {
            name: {
                "model_a_pass": s.get("mean_a", 0) >= 0.5,
                "model_b_pass": s.get("mean_b", 0) >= 0.5,
            }
            for name, s in summary.items()
        },
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=indent, default=str)

    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate JSON evaluation report")
    parser.add_argument("--input", required=True, help="Path to results.json")
    parser.add_argument("--output", default="reports/results_formatted.json")
    args = parser.parse_args()

    with open(args.input) as f:
        data = json.load(f)

    generate_json_report(data, args.output)
    print(f"Report generated: {args.output}")
