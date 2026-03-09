"""
CLI Entry Point for ExaCraft Evaluation Test Bench

Examples:
  # Full evaluation (all 18 scenarios)
  python run_evaluation.py

  # Quick smoke test (3 scenarios)
  python run_evaluation.py --max 3

  # Specific scenarios
  python run_evaluation.py --scenarios T01_recursion_engineer_simple T16_newton_business_simple

  # Only one profile
  python run_evaluation.py --profiles software_engineer_india

  # List available models
  python run_evaluation.py --list-models

  # Check Ollama availability
  python run_evaluation.py --check
"""

import argparse
import sys

from evaluation.judges.ollama_judge import OllamaJudge, OLLAMA_BASE_URL
from evaluation.test_bench import TestBench
from evaluation.test_cases.test_suite import TEST_SCENARIOS, SCENARIO_BY_ID
from evaluation.test_cases.profiles import TEST_PROFILES


def main():
    parser = argparse.ArgumentParser(
        description="ExaCraft LLM-as-Judge Evaluation Test Bench",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--scenarios", nargs="*",
        help="Specific scenario IDs to run (default: all)"
    )
    parser.add_argument(
        "--profiles", nargs="*",
        help="Filter by profile keys (default: all)"
    )
    parser.add_argument(
        "--max", type=int, default=None,
        help="Maximum number of scenarios to run"
    )
    parser.add_argument(
        "--samples", type=int, default=5,
        help="G-Eval samples per dimension per judge (default: 5)"
    )
    parser.add_argument(
        "--run-name", type=str, default=None,
        help="Name for output files"
    )
    parser.add_argument(
        "--output-dir", type=str, default="evaluation/results",
        help="Output directory for reports"
    )
    parser.add_argument(
        "--ollama-url", type=str, default=OLLAMA_BASE_URL,
        help=f"Ollama server URL (default: {OLLAMA_BASE_URL})"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Check Ollama availability and installed models, then exit"
    )
    parser.add_argument(
        "--list-models", action="store_true",
        help="List all locally available Ollama models, then exit"
    )
    parser.add_argument(
        "--list-scenarios", action="store_true",
        help="List all available test scenarios, then exit"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-judge progress output"
    )

    args = parser.parse_args()

    # ── Info commands ──────────────────────────────────────────────────────

    if args.list_scenarios:
        print(f"{'ID':<45} {'Profile':<30} {'Mode':<15} Description")
        print("-" * 110)
        for s in TEST_SCENARIOS:
            print(f"{s.scenario_id:<45} {s.profile_key:<30} {s.generation_mode:<15} {s.description[:40]}")
        return

    if args.list_models or args.check:
        available = OllamaJudge.check_ollama_available(args.ollama_url)
        print(f"Ollama at {args.ollama_url}: {'RUNNING ✓' if available else 'NOT REACHABLE ✗'}")
        if available:
            models = OllamaJudge.list_available_models(args.ollama_url)
            print(f"Installed models ({len(models)}):")
            for m in models:
                print(f"  - {m}")
            if not models:
                print("  No models installed. Run: ollama pull llama3.2:3b mistral:7b phi3:mini")
        return

    # ── Validation ─────────────────────────────────────────────────────────

    if args.scenarios:
        invalid = [s for s in args.scenarios if s not in SCENARIO_BY_ID]
        if invalid:
            print(f"ERROR: Unknown scenario IDs: {invalid}")
            print(f"Run `python run_evaluation.py --list-scenarios` to see available IDs.")
            sys.exit(1)

    if args.profiles:
        invalid = [p for p in args.profiles if p not in TEST_PROFILES]
        if invalid:
            print(f"ERROR: Unknown profile keys: {invalid}")
            print(f"Available: {list(TEST_PROFILES.keys())}")
            sys.exit(1)

    # ── Run ────────────────────────────────────────────────────────────────

    bench = TestBench(
        ollama_url=args.ollama_url,
        n_samples_per_judge=args.samples,
        run_name=args.run_name,
        output_dir=args.output_dir,
    )

    results = bench.run(
        scenario_ids=args.scenarios,
        profile_keys=args.profiles,
        max_scenarios=args.max,
        verbose=not args.quiet,
    )

    if not results:
        print("No results produced.")
        sys.exit(1)

    print(f"\nDone. {len(results)} example(s) evaluated.")


if __name__ == "__main__":
    main()
