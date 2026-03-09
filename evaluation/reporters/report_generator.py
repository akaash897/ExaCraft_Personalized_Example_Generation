"""
Report Generator

Produces two output formats:
  1. JSON — machine-readable, full fidelity for downstream statistical analysis.
  2. HTML — human-readable dashboard for research review and presentation.

The JSON format preserves all raw scores, per-sample data, and reliability metrics,
enabling post-hoc statistical analysis (e.g., mixed-effects models, Mann-Whitney U
tests for mode comparison) in tools like R or Python's scipy.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, List

from evaluation.metrics.aggregator import EvaluationResult, ScoreAggregator
from evaluation.metrics.rubrics import ALL_RUBRICS


class ReportGenerator:
    """Generates JSON and HTML reports from evaluation results."""

    def __init__(self, output_dir: str = "evaluation/results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # ── JSON report ────────────────────────────────────────────────────────

    def save_json(
        self,
        results: List[EvaluationResult],
        run_name: str = None,
    ) -> str:
        """Save full evaluation results as JSON. Returns path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_name = run_name or f"eval_{timestamp}"
        path = os.path.join(self.output_dir, f"{run_name}.json")

        aggregator = ScoreAggregator()
        summary = aggregator.generate_summary_stats(results)

        output = {
            "run_name": run_name,
            "timestamp": datetime.now().isoformat(),
            "n_examples": len(results),
            "judges": list({js.judge_name for r in results for js in r.judge_scores}),
            "summary": summary,
            "results": [self._result_to_dict(r) for r in results],
            "methodology": {
                "scoring_protocol": "G-Eval (Liu et al., 2023) — CoT before scoring, multi-sample averaging",
                "reliability_metric": "Krippendorff's alpha (ordinal, Krippendorff 2011)",
                "bias_mitigations": [
                    "Per-dimension prompting (anti-halo effect)",
                    "Multi-sample averaging N=5 (G-Eval anti-noise)",
                    "Rubric-anchored scoring (anti-verbosity bias)",
                    "Cross-family judge models (anti-self-enhancement bias)",
                    "Blind evaluation — no model attribution in judge prompt",
                ],
                "dimensions": [
                    {"key": r.key, "name": r.name, "weight": r.weight}
                    for r in ALL_RUBRICS
                ],
                "reliability_thresholds": {
                    "high": "alpha >= 0.80",
                    "tentative": "alpha >= 0.667",
                    "unreliable": "alpha < 0.667",
                },
            },
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"JSON report saved: {path}")
        return path

    def _result_to_dict(self, r: EvaluationResult) -> Dict:
        return {
            "topic": r.topic,
            "generation_mode": r.generation_mode,
            "example_text": r.example_text,
            "example_char_length": r.example_char_length,
            "composite_score": r.composite_score,
            "composite_std": r.composite_std,
            "overall_krippendorff_alpha": r.overall_krippendorff_alpha,
            "overall_reliability": r.overall_reliability,
            "user_profile_summary": r.user_profile_summary,
            "learning_context_summary": r.learning_context_summary,
            "dimensions": {
                key: {
                    "name": dim.dimension_name,
                    "mean": dim.mean,
                    "std": dim.std,
                    "min": dim.min_score,
                    "max": dim.max_score,
                    "spread": dim.spread,
                    "krippendorff_alpha": dim.krippendorff_alpha,
                    "agreement_level": dim.agreement_level,
                    "per_judge_scores": dim.scores,
                    "combined_reasoning": dim.combined_reasoning,
                }
                for key, dim in r.dimensions.items()
            },
            "judge_raw_scores": [
                {
                    "judge": js.judge_name,
                    "model": js.model,
                    "composite": js.composite_score,
                    "dimensions": {
                        k: {
                            "score": ds.score,
                            "reasoning": ds.reasoning,
                            "raw_scores": ds.raw_scores,
                            "parse_failures": ds.parse_failures,
                        }
                        for k, ds in js.dimensions.items()
                    },
                }
                for js in r.judge_scores
            ],
        }

    # ── HTML report ────────────────────────────────────────────────────────

    def save_html(
        self,
        results: List[EvaluationResult],
        run_name: str = None,
    ) -> str:
        """Generate an HTML dashboard. Returns path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_name = run_name or f"eval_{timestamp}"
        path = os.path.join(self.output_dir, f"{run_name}.html")

        aggregator = ScoreAggregator()
        summary = aggregator.generate_summary_stats(results)

        html = self._render_html(run_name, summary, results)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"HTML report saved: {path}")
        return path

    def _render_html(
        self,
        run_name: str,
        summary: Dict,
        results: List[EvaluationResult],
    ) -> str:
        dim_rows = ""
        for key, mean in summary.get("per_dimension_means", {}).items():
            rubric = next((r for r in ALL_RUBRICS if r.key == key), None)
            name = rubric.name if rubric else key
            bar_pct = int((mean / 5.0) * 100)
            color = "#4caf50" if mean >= 3.5 else ("#ff9800" if mean >= 2.5 else "#f44336")
            dim_rows += f"""
            <tr>
              <td>{name}</td>
              <td>
                <div style="background:#eee;border-radius:4px;width:200px;display:inline-block;">
                  <div style="background:{color};width:{bar_pct}%;height:14px;border-radius:4px;"></div>
                </div>
                &nbsp;{mean:.2f}
              </td>
            </tr>"""

        result_cards = ""
        for i, r in enumerate(results, 1):
            color = _score_color(r.composite_score)
            contested_dims = [k for k, d in r.dimensions.items() if d.agreement_level == "contested"]
            contested_badge = (
                f'<span style="background:#f44336;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">'
                f'⚠ Contested: {", ".join(contested_dims)}</span>'
                if contested_dims else ""
            )
            alpha_color = (
                "#4caf50" if r.overall_krippendorff_alpha >= 0.80 else
                "#ff9800" if r.overall_krippendorff_alpha >= 0.667 else
                "#f44336"
            )
            dim_detail = ""
            for rubric in ALL_RUBRICS:
                dim = r.dimensions.get(rubric.key)
                if not dim:
                    continue
                scores_str = " | ".join(f"{s:.1f}" for s in dim.scores)
                dim_detail += f"""
                <tr>
                  <td style="font-size:12px;">{dim.dimension_name}</td>
                  <td style="font-size:12px;">{dim.mean:.2f}</td>
                  <td style="font-size:12px;">{scores_str}</td>
                  <td style="font-size:12px;">{dim.agreement_level}</td>
                </tr>"""

            result_cards += f"""
            <div style="border:1px solid #ddd;border-radius:6px;padding:16px;margin-bottom:20px;">
              <h3 style="margin:0 0 8px;">#{i} — {r.topic}
                <span style="font-size:13px;font-weight:normal;color:#666;margin-left:10px;">
                  [{r.generation_mode}]
                </span>
              </h3>
              <div style="background:#f5f5f5;padding:10px;border-radius:4px;font-size:13px;margin-bottom:10px;white-space:pre-wrap;">
{r.example_text}
              </div>
              <table style="font-size:12px;margin-bottom:8px;"><tr>
                <td><b>Composite:</b> <span style="font-size:16px;font-weight:bold;color:{color};">{r.composite_score:.2f}</span>/5.00</td>
                <td style="padding-left:20px;"><b>α:</b> <span style="color:{alpha_color};">{r.overall_krippendorff_alpha:.3f}</span> [{r.overall_reliability}]</td>
                <td style="padding-left:20px;">{contested_badge}</td>
              </tr></table>
              <details>
                <summary style="cursor:pointer;font-size:12px;color:#1976d2;">Dimension breakdown</summary>
                <table style="margin-top:8px;font-size:12px;border-collapse:collapse;width:100%;">
                  <tr style="background:#eee;"><th>Dimension</th><th>Mean</th><th>Per-Judge Scores</th><th>Agreement</th></tr>
                  {dim_detail}
                </table>
              </details>
            </div>"""

        alpha = summary.get("mean_krippendorff_alpha", 0)
        alpha_color_summary = (
            "#4caf50" if alpha >= 0.80 else
            "#ff9800" if alpha >= 0.667 else
            "#f44336"
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ExaCraft Evaluation — {run_name}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 960px; margin: 40px auto; padding: 0 20px; color: #333; }}
    h1 {{ border-bottom: 2px solid #1976d2; padding-bottom: 8px; }}
    h2 {{ color: #1976d2; }}
    table {{ border-collapse: collapse; }}
    td, th {{ padding: 6px 12px; border: 1px solid #e0e0e0; text-align: left; }}
    .metric-card {{ display:inline-block; background:#f5f5f5; border-radius:6px; padding:12px 20px; margin:8px; text-align:center; }}
    .metric-value {{ font-size:28px; font-weight:bold; }}
  </style>
</head>
<body>
  <h1>ExaCraft Evaluation Report</h1>
  <p><b>Run:</b> {run_name} &nbsp;|&nbsp; <b>Generated:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

  <h2>Summary</h2>
  <div>
    <div class="metric-card">
      <div class="metric-value" style="color:{_score_color(summary.get('composite_mean', 0))};">
        {summary.get('composite_mean', 0):.2f}
      </div>
      <div>Mean Composite Score</div>
    </div>
    <div class="metric-card">
      <div class="metric-value" style="color:{alpha_color_summary};">
        {alpha:.3f}
      </div>
      <div>Mean Krippendorff α</div>
    </div>
    <div class="metric-card">
      <div class="metric-value">{summary.get('n_examples', 0)}</div>
      <div>Examples Evaluated</div>
    </div>
    <div class="metric-card">
      <div class="metric-value" style="color:#f44336;">{summary.get('contested_dimension_count', 0)}</div>
      <div>Contested Dimensions</div>
    </div>
  </div>

  <h2>Per-Dimension Means</h2>
  <table>{dim_rows}</table>

  <p style="font-size:12px;color:#666;">{summary.get('verbosity_check', '')}</p>

  <h2>Individual Results</h2>
  {result_cards}

  <hr>
  <p style="font-size:11px;color:#999;">
    Evaluation methodology: G-Eval (Liu et al., 2023) CoT protocol,
    Krippendorff's alpha (ordinal, Krippendorff 2011),
    multi-judge ensemble from 3 model families (Zheng et al., 2023),
    Bloom's Revised Taxonomy pedagogical rubric (Anderson &amp; Krathwohl, 2001).
  </p>
</body>
</html>"""


def _score_color(score: float) -> str:
    if score >= 3.5:
        return "#4caf50"
    elif score >= 2.5:
        return "#ff9800"
    return "#f44336"
