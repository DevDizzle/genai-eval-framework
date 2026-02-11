"""
HTML Report Generator
======================

Generates an interactive HTML evaluation report with embedded charts
using Jinja2 templates and base64-encoded Matplotlib figures.
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from jinja2 import Template


# ---------------------------------------------------------------------------
# Chart generators
# ---------------------------------------------------------------------------

def _fig_to_base64(fig: plt.Figure) -> str:
    """Render a Matplotlib figure to a base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded


def _make_comparison_chart(data: Dict[str, Any]) -> str:
    """Side-by-side bar chart comparing Model A vs Model B scores."""
    summary = data.get("summary", {})
    evaluators = list(summary.keys())
    means_a = [summary[e]["mean_a"] for e in evaluators]
    means_b = [summary[e]["mean_b"] for e in evaluators]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(evaluators))
    width = 0.35

    bars_a = ax.bar(x - width / 2, means_a, width, label=data.get("model_a", "Model A"),
                     color="#4A90D9", alpha=0.85)
    bars_b = ax.bar(x + width / 2, means_b, width, label=data.get("model_b", "Model B"),
                     color="#E8854A", alpha=0.85)

    ax.set_ylabel("Score")
    ax.set_title("Model Comparison — Mean Scores by Evaluator")
    ax.set_xticks(x)
    ax.set_xticklabels([e.replace("_", " ").title() for e in evaluators], rotation=20, ha="right")
    ax.legend()
    ax.set_ylim(0, 1.1)
    ax.grid(axis="y", alpha=0.3)

    # Add value labels
    for bar in bars_a + bars_b:
        height = bar.get_height()
        ax.annotate(f"{height:.2f}", xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)

    return _fig_to_base64(fig)


def _make_radar_chart(data: Dict[str, Any]) -> str:
    """Radar / spider chart comparing models across dimensions."""
    summary = data.get("summary", {})
    evaluators = list(summary.keys())
    n = len(evaluators)
    if n < 3:
        return ""

    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]

    vals_a = [summary[e]["mean_a"] for e in evaluators] + [summary[evaluators[0]]["mean_a"]]
    vals_b = [summary[e]["mean_b"] for e in evaluators] + [summary[evaluators[0]]["mean_b"]]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.plot(angles, vals_a, "o-", linewidth=2, label=data.get("model_a", "Model A"), color="#4A90D9")
    ax.fill(angles, vals_a, alpha=0.15, color="#4A90D9")
    ax.plot(angles, vals_b, "o-", linewidth=2, label=data.get("model_b", "Model B"), color="#E8854A")
    ax.fill(angles, vals_b, alpha=0.15, color="#E8854A")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([e.replace("_", " ").title() for e in evaluators])
    ax.set_ylim(0, 1)
    ax.set_title("Multi-Dimensional Quality Radar", y=1.08)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    return _fig_to_base64(fig)


def _make_significance_chart(data: Dict[str, Any]) -> str:
    """Horizontal bar chart showing p-values with significance threshold."""
    summary = data.get("summary", {})
    evaluators = list(summary.keys())
    p_values = [summary[e].get("p_value", 1.0) for e in evaluators]

    fig, ax = plt.subplots(figsize=(8, 4))
    colors = ["#2ecc71" if p < 0.05 else "#e74c3c" for p in p_values]
    y_pos = np.arange(len(evaluators))

    ax.barh(y_pos, p_values, color=colors, alpha=0.8)
    ax.axvline(x=0.05, color="black", linestyle="--", linewidth=1, label="α = 0.05")
    ax.set_yticks(y_pos)
    ax.set_yticklabels([e.replace("_", " ").title() for e in evaluators])
    ax.set_xlabel("p-value")
    ax.set_title("Statistical Significance by Evaluator")
    ax.legend()
    ax.set_xlim(0, max(max(p_values) * 1.1, 0.1))

    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

HTML_TEMPLATE = Template("""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GenAI Evaluation Report</title>
<style>
  :root { --blue: #4A90D9; --orange: #E8854A; --green: #2ecc71; --red: #e74c3c; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #f5f6fa; color: #2d3436; line-height: 1.6; padding: 2rem; }
  .container { max-width: 1100px; margin: 0 auto; }
  h1 { font-size: 2rem; margin-bottom: 0.5rem; }
  .subtitle { color: #636e72; margin-bottom: 2rem; }
  .card { background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;
          box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
  .card h2 { font-size: 1.3rem; margin-bottom: 1rem; border-bottom: 2px solid #f0f0f0; padding-bottom: 0.5rem; }
  .winner-badge { display: inline-block; padding: 0.3rem 1rem; border-radius: 20px;
                  font-weight: 600; font-size: 1.1rem; }
  .winner-a { background: var(--blue); color: white; }
  .winner-b { background: var(--orange); color: white; }
  .winner-tie { background: #bdc3c7; color: white; }
  table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
  th, td { padding: 0.6rem 1rem; text-align: left; border-bottom: 1px solid #eee; }
  th { background: #fafafa; font-weight: 600; }
  .chart-row { display: flex; gap: 1.5rem; flex-wrap: wrap; }
  .chart-row .card { flex: 1; min-width: 300px; }
  img.chart { width: 100%; height: auto; }
  .sig { font-weight: 600; }
  .sig-yes { color: var(--green); }
  .sig-no { color: var(--red); }
  .meta { font-size: 0.85rem; color: #636e72; }
  @media (max-width: 700px) { .chart-row { flex-direction: column; } }
</style>
</head>
<body>
<div class="container">
  <h1>🔬 GenAI Evaluation Report</h1>
  <p class="subtitle">{{ data.model_a }} vs {{ data.model_b }} — {{ data.num_samples }} samples — {{ data.timestamp }}</p>

  <div class="card">
    <h2>Overall Winner</h2>
    <p>
      {% if data.overall_winner == data.model_a %}
        <span class="winner-badge winner-a">🏆 {{ data.model_a }}</span>
      {% elif data.overall_winner == data.model_b %}
        <span class="winner-badge winner-b">🏆 {{ data.model_b }}</span>
      {% else %}
        <span class="winner-badge winner-tie">🤝 Tie</span>
      {% endif %}
    </p>
  </div>

  <div class="chart-row">
    <div class="card">
      <h2>Score Comparison</h2>
      <img class="chart" src="data:image/png;base64,{{ comparison_chart }}" alt="Comparison Chart">
    </div>
    {% if radar_chart %}
    <div class="card">
      <h2>Quality Radar</h2>
      <img class="chart" src="data:image/png;base64,{{ radar_chart }}" alt="Radar Chart">
    </div>
    {% endif %}
  </div>

  <div class="card">
    <h2>Statistical Significance</h2>
    <img class="chart" src="data:image/png;base64,{{ significance_chart }}" alt="Significance Chart" style="max-width:700px;">
    <table>
      <thead><tr><th>Evaluator</th><th>{{ data.model_a }}</th><th>{{ data.model_b }}</th><th>p-value</th><th>Significant?</th><th>Winner</th></tr></thead>
      <tbody>
      {% for ev, s in data.summary.items() %}
        <tr>
          <td>{{ ev | replace("_", " ") | title }}</td>
          <td>{{ "%.3f" | format(s.mean_a) }} ± {{ "%.3f" | format(s.std_a) }}</td>
          <td>{{ "%.3f" | format(s.mean_b) }} ± {{ "%.3f" | format(s.std_b) }}</td>
          <td>{{ "%.4f" | format(s.p_value) }}</td>
          <td class="sig {% if s.p_value < 0.05 %}sig-yes{% else %}sig-no{% endif %}">
            {{ "Yes ✓" if s.p_value < 0.05 else "No ✗" }}
          </td>
          <td>{{ s.winner | replace("_", " ") | title }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h2>Methodology</h2>
    <ul style="padding-left:1.5rem;">
      <li><strong>Hallucination:</strong> NLI cross-encoder + sentence embedding similarity</li>
      <li><strong>Factual Accuracy:</strong> Claim extraction + semantic/numerical verification</li>
      <li><strong>Content Safety:</strong> Detoxify toxicity + brand alignment + PII detection</li>
      <li><strong>Quality:</strong> LLM-as-judge (coherence, fluency, relevance)</li>
      <li><strong>Statistics:</strong> Paired t-test (n≥30) or Wilcoxon signed-rank (n&lt;30), α=0.05</li>
    </ul>
  </div>

  <p class="meta">Generated by GenAI Evaluation Framework</p>
</div>
</body>
</html>
""")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_html_report(
    data: Dict[str, Any],
    output_path: str,
    extra_charts: Optional[Dict[str, str]] = None,
) -> str:
    """Generate an HTML evaluation report.

    Args:
        data: Benchmark result dict (from BenchmarkResult.to_dict()).
        output_path: Where to write the HTML file.
        extra_charts: Optional dict of name -> base64 PNG to embed.

    Returns:
        The output file path.
    """
    comparison_chart = _make_comparison_chart(data)
    radar_chart = _make_radar_chart(data)
    significance_chart = _make_significance_chart(data)

    html = HTML_TEMPLATE.render(
        data=data,
        comparison_chart=comparison_chart,
        radar_chart=radar_chart,
        significance_chart=significance_chart,
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate HTML evaluation report")
    parser.add_argument("--input", required=True, help="Path to results.json")
    parser.add_argument("--output", default="reports/report.html")
    args = parser.parse_args()

    with open(args.input) as f:
        data = json.load(f)

    generate_html_report(data, args.output)
    print(f"Report generated: {args.output}")
