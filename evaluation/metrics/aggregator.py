"""
Score Aggregation and Inter-Rater Reliability

Core methods:
  - Krippendorff's alpha (ordinal): gold-standard multi-rater reliability metric.
    Unlike Cohen's kappa (two-rater only) or ICC (assumes interval data),
    Krippendorff's alpha handles arbitrary numbers of raters on ordinal scales
    with missing data — perfectly suited for 3 LLM judges scoring 1–5.
    (Krippendorff, 2011; Hayes & Krippendorff, 2007)

  - Composite score: weighted mean of 7 dimension scores, weights from rubrics.

  - Verbosity bias check: Pearson correlation between example length (chars) and
    composite score. |r| > 0.20 flags a verbosity bias concern.
    (Wang et al., 2023 — quantified ~10-15% verbosity inflation in GPT-4 judges)

  - Disagreement protocol (Zheng et al., 2023):
    * spread ≤ 1: accept weighted average (minor disagreement)
    * spread == 2: flag moderate disagreement, report variance
    * spread ≥ 3: flag for human review ("contested")

Target thresholds (Krippendorff's own standards):
  α ≥ 0.80: High reliability
  α ≥ 0.667: Tentative conclusions
  α < 0.667: Unreliable — rubric needs refinement
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from evaluation.metrics.rubrics import ALL_RUBRICS, Rubric
# Import directly from module (not package __init__) to avoid circular imports
from evaluation.judges.base_judge import JudgeScore, DimensionScore


@dataclass
class DimensionAggregated:
    """Aggregated scores for one dimension across all judges."""
    dimension_key: str
    dimension_name: str
    scores: List[float]                    # one per judge
    mean: float
    std: float
    min_score: float
    max_score: float
    spread: float                           # max - min
    krippendorff_alpha: float              # per-dimension reliability
    agreement_level: str                   # "strong" | "moderate" | "weak" | "contested"
    combined_reasoning: List[str]          # reasoning from each judge


@dataclass
class EvaluationResult:
    """
    Complete evaluation result for one example, aggregated across all judges.

    This is the primary output object of the evaluation framework.
    """
    topic: str
    example_text: str
    user_profile_summary: str
    learning_context_summary: str
    generation_mode: str                   # "simple" | "adaptive" | "collaborative"
    judge_scores: List[JudgeScore]         # raw per-judge scores
    dimensions: Dict[str, DimensionAggregated] = field(default_factory=dict)
    composite_score: float = 0.0           # weighted aggregate
    composite_std: float = 0.0
    overall_krippendorff_alpha: float = 0.0
    overall_reliability: str = ""          # "high" | "tentative" | "unreliable"
    verbosity_note: str = ""               # set if length bias suspected
    example_char_length: int = 0
    metadata: Dict = field(default_factory=dict)


class ScoreAggregator:
    """Aggregates JudgeScore objects into a final EvaluationResult."""

    # Disagreement thresholds (Zheng et al., 2023)
    SPREAD_MODERATE = 2
    SPREAD_CONTESTED = 3

    # Reliability thresholds (Krippendorff, 2011)
    ALPHA_HIGH = 0.80
    ALPHA_TENTATIVE = 0.667

    # Verbosity bias flag (Wang et al., 2023)
    VERBOSITY_CORRELATION_THRESHOLD = 0.20

    def aggregate(
        self,
        topic: str,
        example_text: str,
        user_profile_summary: str,
        learning_context_summary: str,
        generation_mode: str,
        judge_scores: List[JudgeScore],
    ) -> EvaluationResult:
        """
        Aggregate multiple JudgeScore objects into one EvaluationResult.

        Steps:
          1. Collect per-dimension scores from all judges.
          2. Compute mean, std, spread per dimension.
          3. Compute Krippendorff's alpha per dimension.
          4. Determine agreement level and flag contested dimensions.
          5. Compute weighted composite score.
          6. Compute overall Krippendorff's alpha across all dimensions.
        """
        result = EvaluationResult(
            topic=topic,
            example_text=example_text,
            user_profile_summary=user_profile_summary,
            learning_context_summary=learning_context_summary,
            generation_mode=generation_mode,
            judge_scores=judge_scores,
            example_char_length=len(example_text),
        )

        if not judge_scores:
            return result

        # ── Per-dimension aggregation ──────────────────────────────────────
        all_dim_scores_matrix: List[List[float]] = []  # for overall alpha

        for rubric in ALL_RUBRICS:
            scores_for_dim: List[float] = []
            reasonings: List[str] = []

            for js in judge_scores:
                dim = js.dimensions.get(rubric.key)
                if dim:
                    scores_for_dim.append(dim.score)
                    reasonings.append(f"[{js.judge_name}]: {dim.reasoning}")

            if not scores_for_dim:
                continue

            mean_s = sum(scores_for_dim) / len(scores_for_dim)
            std_s = _std(scores_for_dim)
            min_s = min(scores_for_dim)
            max_s = max(scores_for_dim)
            spread = max_s - min_s
            alpha = _krippendorff_alpha_ordinal(scores_for_dim, scale_max=5)
            agreement = self._agreement_level(spread)

            result.dimensions[rubric.key] = DimensionAggregated(
                dimension_key=rubric.key,
                dimension_name=rubric.name,
                scores=scores_for_dim,
                mean=round(mean_s, 3),
                std=round(std_s, 3),
                min_score=min_s,
                max_score=max_s,
                spread=spread,
                krippendorff_alpha=round(alpha, 3),
                agreement_level=agreement,
                combined_reasoning=reasonings,
            )

            all_dim_scores_matrix.append(scores_for_dim)

        # ── Composite score ────────────────────────────────────────────────
        composite_per_judge = [js.composite_score for js in judge_scores]
        result.composite_score = round(sum(composite_per_judge) / len(composite_per_judge), 3)
        result.composite_std = round(_std(composite_per_judge), 3)

        # ── Overall Krippendorff's alpha ────────────────────────────────────
        # Flatten: treat each (judge × dimension) pair as a rater-item observation.
        # We compute alpha over the transposed matrix (raters × items).
        if all_dim_scores_matrix:
            n_judges = len(judge_scores)
            n_dims = len(all_dim_scores_matrix)
            # reliability_data[judge_idx][dim_idx]
            rater_matrix = []
            for j_idx in range(n_judges):
                row = []
                for d_idx in range(n_dims):
                    try:
                        row.append(all_dim_scores_matrix[d_idx][j_idx])
                    except IndexError:
                        row.append(float("nan"))
                rater_matrix.append(row)

            result.overall_krippendorff_alpha = round(
                _krippendorff_alpha_ordinal_matrix(rater_matrix, scale_max=5), 3
            )

        # ── Reliability label ──────────────────────────────────────────────
        alpha = result.overall_krippendorff_alpha
        if alpha >= self.ALPHA_HIGH:
            result.overall_reliability = "high"
        elif alpha >= self.ALPHA_TENTATIVE:
            result.overall_reliability = "tentative"
        else:
            result.overall_reliability = "unreliable"

        return result

    def _agreement_level(self, spread: float) -> str:
        if spread < self.SPREAD_MODERATE:
            return "strong"
        elif spread < self.SPREAD_CONTESTED:
            return "moderate"
        else:
            return "contested"

    def check_verbosity_bias(self, results: List[EvaluationResult]) -> Tuple[float, str]:
        """
        Compute Pearson correlation between example length and composite score
        across a set of results.

        Wang et al. (2023): |r| > 0.20 suggests verbosity bias is present.

        Returns:
            (correlation, note_string)
        """
        if len(results) < 3:
            return 0.0, "Insufficient data for verbosity bias check (need ≥ 3 results)."

        lengths = [r.example_char_length for r in results]
        scores = [r.composite_score for r in results]
        r = _pearson(lengths, scores)

        if abs(r) > self.VERBOSITY_CORRELATION_THRESHOLD:
            note = (
                f"VERBOSITY BIAS WARNING: Pearson r={r:.3f} between example length "
                f"and composite score exceeds threshold ±{self.VERBOSITY_CORRELATION_THRESHOLD}. "
                f"Judge scores may be inflated by longer examples. "
                f"Consider adding explicit anti-verbosity instructions to judge prompts."
            )
        else:
            note = f"Verbosity bias check passed (r={r:.3f}, threshold ±{self.VERBOSITY_CORRELATION_THRESHOLD})."

        return r, note

    def generate_summary_stats(self, results: List[EvaluationResult]) -> Dict:
        """Compute summary statistics across a batch of evaluation results."""
        if not results:
            return {}

        composites = [r.composite_score for r in results]
        alpha_values = [r.overall_krippendorff_alpha for r in results]

        per_dim_means: Dict[str, List[float]] = {}
        for r in results:
            for key, dim in r.dimensions.items():
                per_dim_means.setdefault(key, []).append(dim.mean)

        contested_count = sum(
            1 for r in results
            for dim in r.dimensions.values()
            if dim.agreement_level == "contested"
        )

        _, verbosity_note = self.check_verbosity_bias(results)

        return {
            "n_examples": len(results),
            "composite_mean": round(sum(composites) / len(composites), 3),
            "composite_std": round(_std(composites), 3),
            "composite_min": min(composites),
            "composite_max": max(composites),
            "mean_krippendorff_alpha": round(sum(alpha_values) / len(alpha_values), 3),
            "contested_dimension_count": contested_count,
            "per_dimension_means": {
                k: round(sum(v) / len(v), 3) for k, v in per_dim_means.items()
            },
            "verbosity_check": verbosity_note,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Statistical helpers
# ──────────────────────────────────────────────────────────────────────────────

def _std(values: List[float]) -> float:
    """Population standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((x - mean) ** 2 for x in values) / len(values))


def _pearson(x: List[float], y: List[float]) -> float:
    """Pearson correlation coefficient."""
    n = len(x)
    if n < 2:
        return 0.0
    mx, my = sum(x) / n, sum(y) / n
    num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    den = math.sqrt(
        sum((x[i] - mx) ** 2 for i in range(n)) *
        sum((y[i] - my) ** 2 for i in range(n))
    )
    return num / den if den > 0 else 0.0


def _krippendorff_alpha_ordinal(scores: List[float], scale_max: int = 5) -> float:
    """
    Krippendorff's alpha for ordinal data — single-item, multiple raters.

    For a single item with N rater scores, alpha is computed using the
    ordinal distance metric: d(k, l) = (k - l)^2 (standard for ordinal scales).

    With only one item, expected disagreement = variance across all possible
    value pairs weighted by the nominal distribution, approximated here using
    the theoretical uniform distribution on [1, scale_max].

    Reference: Krippendorff (2011) "Computing Krippendorff's Alpha-Reliability"
    """
    if len(scores) < 2:
        return 1.0  # Perfect reliability with one rater

    n = len(scores)
    # Observed disagreement: mean pairwise squared distance
    d_o = sum(
        (scores[i] - scores[j]) ** 2
        for i in range(n) for j in range(n) if i != j
    ) / (n * (n - 1))

    # Expected disagreement under uniform distribution on {1, ..., scale_max}
    vals = list(range(1, scale_max + 1))
    k = len(vals)
    d_e = sum(
        (vals[i] - vals[j]) ** 2
        for i in range(k) for j in range(k)
    ) / (k * k)

    if d_e == 0:
        return 1.0
    return 1.0 - d_o / d_e


def _krippendorff_alpha_ordinal_matrix(
    rater_matrix: List[List[float]], scale_max: int = 5
) -> float:
    """
    Krippendorff's alpha for ordinal data — multiple raters, multiple items.

    rater_matrix[i][j] = score given by rater i to item j (NaN for missing).

    Uses the standard ordinal distance metric d(k,l) = (k-l)^2.

    Reference: Krippendorff (2004) "Content Analysis: An Introduction to Its Methodology"
    """
    n_raters = len(rater_matrix)
    if n_raters == 0:
        return 0.0
    n_items = len(rater_matrix[0]) if rater_matrix else 0
    if n_items == 0:
        return 0.0

    # Build pairing list: all (v_ik, v_jk) for i≠j, same item k
    coincidences: List[Tuple[float, float]] = []
    for k in range(n_items):
        item_scores = []
        for i in range(n_raters):
            v = rater_matrix[i][k]
            if not math.isnan(v):
                item_scores.append(v)
        m_k = len(item_scores)
        if m_k < 2:
            continue
        for a in range(m_k):
            for b in range(m_k):
                if a != b:
                    coincidences.append((item_scores[a], item_scores[b]))

    if not coincidences:
        return 0.0

    # Observed disagreement
    d_o = sum((u - v) ** 2 for u, v in coincidences) / len(coincidences)

    # Expected disagreement — frequency distribution of all values
    all_values = [v for u, v in coincidences]
    total = len(all_values)
    freq: Dict[float, int] = {}
    for v in all_values:
        freq[v] = freq.get(v, 0) + 1

    d_e = 0.0
    value_list = list(freq.keys())
    for vi in value_list:
        for vj in value_list:
            p_vi = freq[vi] / total
            p_vj = freq[vj] / total
            d_e += (vi - vj) ** 2 * p_vi * p_vj

    if d_e == 0:
        return 1.0

    return 1.0 - d_o / d_e
