"""
ExaCraft Test Bench — Main Orchestrator

Wires together:
  1. Test scenario definitions (profile × topic × mode)
  2. ExaCraft example generators (simple / adaptive / collaborative)
  3. LLM judge ensemble (3 Ollama models)
  4. Score aggregation with Krippendorff's alpha
  5. Report generation (JSON + HTML)

Usage:
  from evaluation.test_bench import TestBench
  bench = TestBench()
  bench.run()
"""

from __future__ import annotations

import os
import sys
import time
from typing import List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.example_generator import ExampleGenerator
from core.user_profile import UserProfile

from evaluation.judges.ollama_judge import OllamaJudge, build_judge_panel, OLLAMA_BASE_URL
from evaluation.judges.judge_ensemble import JudgeEnsemble
from evaluation.metrics.aggregator import EvaluationResult, ScoreAggregator
from evaluation.reporters.report_generator import ReportGenerator
from evaluation.test_cases.profiles import TEST_PROFILES
from evaluation.test_cases.test_suite import TEST_SCENARIOS, TestScenario, SCENARIO_BY_ID


class TestBench:
    """
    End-to-end evaluation orchestrator for ExaCraft.

    Generates examples using the real ExaCraft pipeline, then passes them
    through the LLM judge ensemble for scoring.
    """

    def __init__(
        self,
        ollama_url: str = OLLAMA_BASE_URL,
        n_samples_per_judge: int = 5,
        run_name: str = None,
        output_dir: str = "evaluation/results",
        gemini_api_key: str = None,
    ):
        """
        Args:
            ollama_url: URL of local Ollama server.
            n_samples_per_judge: G-Eval samples per dimension per judge (default 5).
            run_name: Name for the output files. Auto-generated if None.
            output_dir: Directory for JSON/HTML output.
            gemini_api_key: Gemini API key (falls back to GEMINI_API_KEY env var).
        """
        self.ollama_url = ollama_url
        self.n_samples = n_samples_per_judge
        self.run_name = run_name or f"eval_{int(time.time())}"
        self.output_dir = output_dir

        # Load environment
        from dotenv import load_dotenv
        load_dotenv()

        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.generator: Optional[ExampleGenerator] = None
        self.ensemble: Optional[JudgeEnsemble] = None
        self.reporter = ReportGenerator(output_dir=output_dir)

    def setup(self) -> bool:
        """
        Initialize generator and judge ensemble.
        Returns False if critical components are unavailable.
        """
        print("═" * 60)
        print("  ExaCraft Evaluation Test Bench")
        print("═" * 60)

        # ── Generator ──────────────────────────────────────────────────────
        if not self.gemini_api_key:
            print("ERROR: GEMINI_API_KEY not found. Set it in .env or pass as argument.")
            return False

        try:
            self.generator = ExampleGenerator(api_key=self.gemini_api_key)
            print(f"Generator: Gemini ({self.generator.model_config['model']})")
        except Exception as e:
            print(f"ERROR: Failed to initialize ExampleGenerator: {e}")
            return False

        # ── Judge ensemble ─────────────────────────────────────────────────
        if not OllamaJudge.check_ollama_available(self.ollama_url):
            print(f"ERROR: Ollama server not reachable at {self.ollama_url}")
            print("  Start Ollama with: ollama serve")
            return False

        judges = build_judge_panel(base_url=self.ollama_url, n_samples=self.n_samples)
        if not judges:
            print("ERROR: No Ollama models available.")
            print("  Install models with: ollama pull llama3.2:3b mistral:7b phi3:mini")
            return False

        self.ensemble = JudgeEnsemble(judges=judges)
        print(f"Judge ensemble: {len(judges)} model(s) loaded")
        print()

        return True

    def run(
        self,
        scenario_ids: List[str] = None,
        profile_keys: List[str] = None,
        max_scenarios: int = None,
        verbose: bool = True,
    ) -> List[EvaluationResult]:
        """
        Run the full evaluation pipeline.

        Args:
            scenario_ids: If given, only run these specific scenario IDs.
            profile_keys: If given, only run scenarios for these profiles.
            max_scenarios: Limit total scenarios (useful for quick smoke tests).
            verbose: Print progress.

        Returns:
            List of EvaluationResult objects.
        """
        if not self.setup():
            return []

        # Filter scenarios
        scenarios = list(TEST_SCENARIOS)
        if scenario_ids:
            scenarios = [s for s in scenarios if s.scenario_id in scenario_ids]
        if profile_keys:
            scenarios = [s for s in scenarios if s.profile_key in profile_keys]
        if max_scenarios:
            scenarios = scenarios[:max_scenarios]

        if not scenarios:
            print("No scenarios matched the given filters.")
            return []

        print(f"Running {len(scenarios)} scenario(s)...")
        print()

        results: List[EvaluationResult] = []

        for i, scenario in enumerate(scenarios, 1):
            print(f"[{i}/{len(scenarios)}] {scenario.scenario_id}")
            print(f"  Topic  : {scenario.topic}")
            print(f"  Profile: {scenario.profile_key}")
            print(f"  Mode   : {scenario.generation_mode}")

            result = self._run_scenario(scenario, verbose=verbose)
            if result:
                results.append(result)

        # ── Reports ───────────────────────────────────────────────────────
        if results:
            print("\n" + "═" * 60)
            print("  Generating reports...")
            self.reporter.save_json(results, run_name=self.run_name)
            self.reporter.save_html(results, run_name=self.run_name)

            # Print overall summary
            agg = ScoreAggregator()
            summary = agg.generate_summary_stats(results)
            print(f"\n  FINAL SUMMARY")
            print(f"  Composite mean    : {summary['composite_mean']:.2f} / 5.00")
            print(f"  Mean Krippendorff α: {summary['mean_krippendorff_alpha']:.3f}")
            print(f"  Contested dims    : {summary['contested_dimension_count']}")
            print(f"  {summary['verbosity_check']}")

        return results

    def _run_scenario(
        self,
        scenario: TestScenario,
        verbose: bool = True,
    ) -> Optional[EvaluationResult]:
        """Generate example + evaluate for one scenario."""
        profile_data = TEST_PROFILES.get(scenario.profile_key)
        if not profile_data:
            print(f"  ERROR: Profile '{scenario.profile_key}' not found.")
            return None

        # ── Generate example ───────────────────────────────────────────────
        try:
            example_text = self._generate_example(scenario, profile_data)
        except Exception as e:
            print(f"  ERROR generating example: {e}")
            return None

        if example_text.startswith("Error generating example:"):
            print(f"  ERROR: {example_text}")
            return None

        print(f"  Example ({len(example_text)} chars): {example_text[:120]}...")

        # ── Build context summaries for judges ─────────────────────────────
        user_profile = UserProfile(profile_data=profile_data)
        profile_summary = user_profile.get_profile_summary()
        context_summary = scenario.learning_context.to_context_summary()

        # ── Evaluate ───────────────────────────────────────────────────────
        result = self.ensemble.evaluate(
            topic=scenario.topic,
            user_profile_summary=profile_summary,
            learning_context_summary=context_summary,
            example_text=example_text,
            generation_mode=scenario.generation_mode,
            verbose=verbose,
        )

        result.metadata.update({
            "scenario_id": scenario.scenario_id,
            "profile_key": scenario.profile_key,
            "learning_context_name": scenario.learning_context.scenario_name,
        })

        return result

    def _generate_example(self, scenario: TestScenario, profile_data: dict) -> str:
        """Route to the correct ExampleGenerator method based on mode."""
        mode = scenario.generation_mode

        if mode == "simple":
            return self.generator.generate_example_simple(
                topic=scenario.topic,
                profile_data=profile_data,
            )

        elif mode == "adaptive":
            # Use simulated context summary directly by patching the call.
            # We pass user_id=None and inject context via the profile snapshot
            # to avoid touching real learning_contexts/ files.
            user_profile = UserProfile(profile_data=profile_data)
            from core.learning_context import LearningContext

            # Build a synthetic LearningContext from the simulation
            lc = LearningContext(user_id=None)
            lc.context_data = {
                "recent_topics": [
                    {"topic": t, "timestamp": "2024-01-01T00:00:00"}
                    for t in scenario.learning_context.recent_topics
                ],
                "struggle_indicators": {
                    t: {"repeat_count": 3, "last_seen": "2024-01-01T00:00:00"}
                    for t in scenario.learning_context.struggle_topics
                },
                "mastery_indicators": (
                    {
                        "mastery_sim": {
                            "type": "quick_progression",
                            "topics": scenario.learning_context.mastery_topics,
                            "unique_topic_count": len(scenario.learning_context.mastery_topics),
                            "timestamp": "2024-01-01T00:00:00",
                        }
                    }
                    if scenario.learning_context.mastery_topics else {}
                ),
                "session_history": [],
            }

            return self.generator.generate_example(
                topic=scenario.topic,
                user_profile=user_profile,
                learning_context=lc,
            )

        elif mode == "collaborative":
            result = self.generator.generate_collaborative_example(
                topic=scenario.topic,
                profile_data=profile_data,
                user_id=profile_data.get("user_id"),
                record_history=False,
            )
            return result.get("example", "Error: no example in collaborative result")

        else:
            raise ValueError(f"Unknown generation mode: {mode}")

    def evaluate_single(
        self,
        topic: str,
        example_text: str,
        profile_data: dict,
        learning_context_summary: str = "First time learning session",
        generation_mode: str = "manual",
        verbose: bool = True,
    ) -> EvaluationResult:
        """
        Evaluate a single pre-generated example (no generation step).

        Useful for testing specific examples or comparing against baselines.
        """
        if not self.ensemble:
            self.setup()

        user_profile = UserProfile(profile_data=profile_data)
        profile_summary = user_profile.get_profile_summary()

        return self.ensemble.evaluate(
            topic=topic,
            user_profile_summary=profile_summary,
            learning_context_summary=learning_context_summary,
            example_text=example_text,
            generation_mode=generation_mode,
            verbose=verbose,
        )
