"""
Multi-Judge Ensemble

Runs multiple OllamaJudge instances and aggregates into one EvaluationResult.

Rationale for 3-judge ensemble (Zheng et al., 2023; Wang et al., 2023):
  - One judge achieves ~80% human agreement; three judges from different families
    reduce correlated errors and approach ~85-90% agreement.
  - Three is the minimum for majority voting without ties.
  - Five+ judges show diminishing returns beyond cost.
  - Judges run sequentially (not parallel) to avoid Ollama memory contention
    when loading multiple large models simultaneously.
"""

from __future__ import annotations

import time
from typing import List, Optional

from evaluation.judges.base_judge import JudgeScore
from evaluation.judges.ollama_judge import OllamaJudge
from evaluation.metrics.aggregator import ScoreAggregator, EvaluationResult


class JudgeEnsemble:
    """
    Coordinates multiple OllamaJudge instances for ensemble evaluation.

    Each judge independently evaluates the example.
    Scores are then aggregated with inter-rater reliability measurement.
    """

    def __init__(self, judges: List[OllamaJudge]):
        if not judges:
            raise ValueError("At least one judge is required.")
        self.judges = judges
        self.aggregator = ScoreAggregator()

    def evaluate(
        self,
        topic: str,
        user_profile_summary: str,
        learning_context_summary: str,
        example_text: str,
        generation_mode: str = "adaptive",
        verbose: bool = True,
    ) -> EvaluationResult:
        """
        Run all judges and aggregate results.

        Args:
            topic: Concept being illustrated.
            user_profile_summary: Formatted user profile string.
            learning_context_summary: Formatted learning context string.
            example_text: The generated example to evaluate.
            generation_mode: "simple" | "adaptive" | "collaborative"
            verbose: Print progress to stdout.

        Returns:
            Aggregated EvaluationResult with reliability metrics.
        """
        judge_scores: List[JudgeScore] = []

        for judge in self.judges:
            if verbose:
                print(f"  Running judge: {judge.name} ({judge.model})...")
            t0 = time.time()

            score = judge.evaluate(
                topic=topic,
                user_profile_summary=user_profile_summary,
                learning_context_summary=learning_context_summary,
                example_text=example_text,
            )
            elapsed = time.time() - t0

            if verbose:
                print(f"    Done in {elapsed:.1f}s. Composite: {score.composite_score:.2f}")

            judge_scores.append(score)

        result = self.aggregator.aggregate(
            topic=topic,
            example_text=example_text,
            user_profile_summary=user_profile_summary,
            learning_context_summary=learning_context_summary,
            generation_mode=generation_mode,
            judge_scores=judge_scores,
        )

        if verbose:
            self._print_summary(result)

        return result

    @staticmethod
    def _print_summary(result: EvaluationResult):
        alpha = result.overall_krippendorff_alpha
        reliability = result.overall_reliability
        print(f"\n  ── Evaluation Summary ──")
        print(f"  Composite score : {result.composite_score:.2f} / 5.00  (±{result.composite_std:.2f})")
        print(f"  Krippendorff α  : {alpha:.3f} [{reliability}]")
        contested = [k for k, d in result.dimensions.items() if d.agreement_level == "contested"]
        if contested:
            print(f"  Contested dims  : {', '.join(contested)}")
        print()
