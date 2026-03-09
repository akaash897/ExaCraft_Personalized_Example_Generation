"""
Abstract base for all LLM judges.

Design rationale:
  - Each judge evaluates one example across all 7 dimensions.
  - Per-dimension prompting (calling the model once per dimension) is used instead
    of a single mega-prompt. This avoids the halo effect (Nisbett & Wilson, 1977):
    early high scores on one criterion inflate subsequent scores when evaluated
    together. Independent prompts isolate each criterion.
  - Multi-sample averaging (G-Eval, Liu et al. 2023): each judge is called N_SAMPLES
    times per dimension at low temperature. The average score approximates the
    expected value over the model's output distribution, yielding continuous scores
    that correlate better with human judgments than a single greedy decoding.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from evaluation.metrics.rubrics import ALL_RUBRICS, Rubric, build_judge_prompt


@dataclass
class DimensionScore:
    """Score for a single evaluation dimension from one judge."""
    dimension_key: str
    score: float            # 1.0–5.0 (averaged across samples)
    reasoning: str          # reasoning from the last/best sample
    raw_scores: List[float] = field(default_factory=list)  # per-sample scores
    parse_failures: int = 0  # number of samples that failed JSON parsing


@dataclass
class JudgeScore:
    """Complete evaluation result from one judge for one example."""
    judge_name: str
    model: str
    topic: str
    example_text: str
    dimensions: Dict[str, DimensionScore] = field(default_factory=dict)
    composite_score: float = 0.0   # weighted sum using rubric weights
    evaluation_metadata: Dict = field(default_factory=dict)

    def compute_composite(self) -> float:
        """Compute weighted composite score from rubric weights."""
        total = 0.0
        for rubric in ALL_RUBRICS:
            dim = self.dimensions.get(rubric.key)
            if dim:
                total += dim.score * rubric.weight
        self.composite_score = total
        return self.composite_score


class BaseJudge(ABC):
    """
    Abstract base for LLM judges.

    Subclasses implement `_call_model(prompt, temperature, n_samples)` which
    returns a list of raw text responses from the model.
    """

    # Number of samples per dimension for probability-weighted averaging.
    # G-Eval used 20; we use 5 by default for speed with local models.
    N_SAMPLES: int = 5
    JUDGE_TEMPERATURE: float = 0.3   # Low temp for consistency

    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model

    @abstractmethod
    def _call_model(self, prompt: str, temperature: float, n_samples: int) -> List[str]:
        """
        Call the underlying LLM.

        Args:
            prompt: Full evaluation prompt.
            temperature: Sampling temperature.
            n_samples: Number of independent samples to draw.

        Returns:
            List of raw text responses (length == n_samples where possible).
        """

    def evaluate(
        self,
        topic: str,
        user_profile_summary: str,
        learning_context_summary: str,
        example_text: str,
    ) -> JudgeScore:
        """
        Evaluate an example across all 7 dimensions.

        Bias mitigations applied:
          1. Per-dimension prompts (anti-halo)
          2. Multi-sample averaging (G-Eval anti-noise)
          3. No model attribution in prompt (anti-familiarity bias)
          4. Explicit rubric anchors in prompt (anti-verbosity bias via criteria)
        """
        result = JudgeScore(
            judge_name=self.name,
            model=self.model,
            topic=topic,
            example_text=example_text,
        )

        for rubric in ALL_RUBRICS:
            prompt = build_judge_prompt(
                topic=topic,
                user_profile_summary=user_profile_summary,
                learning_context_summary=learning_context_summary,
                example_text=example_text,
                rubric=rubric,
            )
            dim_score = self._evaluate_dimension(prompt, rubric)
            result.dimensions[rubric.key] = dim_score

        result.compute_composite()
        return result

    def _evaluate_dimension(self, prompt: str, rubric: Rubric) -> DimensionScore:
        """
        Evaluate one dimension using multi-sample averaging.

        Parse failures are tolerated: if a sample fails to parse, it is skipped.
        If ALL samples fail, a score of 3 (neutral) is assigned with a warning.
        """
        responses = self._call_model(prompt, self.JUDGE_TEMPERATURE, self.N_SAMPLES)

        scores: List[float] = []
        last_reasoning = ""
        parse_failures = 0

        for raw in responses:
            parsed = self._parse_response(raw)
            if parsed is None:
                parse_failures += 1
                continue
            scores.append(float(parsed["score"]))
            last_reasoning = parsed.get("reasoning", "")

        if not scores:
            # All samples failed: assign neutral score, flag degraded quality
            return DimensionScore(
                dimension_key=rubric.key,
                score=3.0,
                reasoning="[PARSE FAILURE: all samples failed to produce valid JSON]",
                raw_scores=[],
                parse_failures=parse_failures,
            )

        avg_score = sum(scores) / len(scores)
        # Clamp to valid range in case of edge cases
        avg_score = max(1.0, min(5.0, avg_score))

        return DimensionScore(
            dimension_key=rubric.key,
            score=avg_score,
            reasoning=last_reasoning,
            raw_scores=scores,
            parse_failures=parse_failures,
        )

    @staticmethod
    def _parse_response(raw: str) -> Optional[Dict]:
        """
        Extract JSON from model response.

        Handles:
          - Clean JSON
          - JSON embedded in markdown code fences
          - Trailing text after valid JSON
        """
        if not raw:
            return None

        # Try to extract JSON block from markdown fences
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if fence_match:
            raw = fence_match.group(1)

        # Try to find first complete JSON object
        brace_start = raw.find("{")
        if brace_start == -1:
            return None

        # Find matching closing brace
        depth = 0
        for i, ch in enumerate(raw[brace_start:], start=brace_start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    json_str = raw[brace_start : i + 1]
                    try:
                        data = json.loads(json_str)
                        score = data.get("score")
                        if isinstance(score, (int, float)) and 1 <= score <= 5:
                            return data
                    except json.JSONDecodeError:
                        pass
                    break

        return None
