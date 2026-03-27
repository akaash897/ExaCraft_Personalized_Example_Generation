"""
Main Evaluation Loop
Runs the full ablation study across all tiers, users, and topics.
Supports checkpoint/resume — saves progress to results/ after each (user, topic, tier).

Usage:
  python eval/run_evaluation.py [--tiers t0 t1 t2 t3] [--users 1-5] [--topics 0-9]
                                [--provider openai|openrouter] [--judge-model gpt-4o]
                                [--delay 2.0] [--judge-delay 1.5] [--dry-run]

Results saved to: eval/results/scores_{tier}_{user_id}_{topic_slug}.json
Checkpoint index:  eval/results/checkpoint.json
"""

import sys
import os
import json
import time
import argparse
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Optional, Dict, Any
from datetime import datetime

from eval.synthetic_profiles import SYNTHETIC_PROFILES, TOPICS, get_expected_decision
from eval.baseline_runners import run_tier0, run_tier1, run_tier2, run_tier3, reset_manager
from eval.llm_judge import judge_example, judge_feedback_compliance, judge_pairwise_pf, judge_instruction_specificity
from core.feedback_store import load_learning_patterns, load_accept_insights

_BASE_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
RESULTS_DIR = _BASE_RESULTS_DIR          # may be overridden by --run-tag
CHECKPOINT_FILE = os.path.join(RESULTS_DIR, "checkpoint.json")

TIER_RUNNERS = {
    "t0": run_tier0,
    "t1": run_tier1,
    "t2": run_tier2,
    "t3": run_tier3,
}


def _set_results_dir(run_tag: str) -> None:
    """Point all path helpers at a tag-specific subdirectory."""
    global RESULTS_DIR, CHECKPOINT_FILE
    if run_tag:
        RESULTS_DIR = os.path.join(_BASE_RESULTS_DIR, run_tag)
    else:
        RESULTS_DIR = _BASE_RESULTS_DIR
    CHECKPOINT_FILE = os.path.join(RESULTS_DIR, "checkpoint.json")
    os.makedirs(RESULTS_DIR, exist_ok=True)


# ── Checkpoint Helpers ────────────────────────────────────────────────────────

def _load_checkpoint() -> set:
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            data = json.load(f)
        return set(data.get("completed", []))
    return set()


def _save_checkpoint(completed: set) -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"completed": sorted(completed), "updated_at": datetime.now().isoformat()}, f, indent=2)


def _result_key(tier: str, user_id: str, topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")
    return f"{tier}__{user_id}__{slug}"


def _result_path(tier: str, user_id: str, topic: str) -> str:
    key = _result_key(tier, user_id, topic)
    return os.path.join(RESULTS_DIR, f"scores_{key}.json")


def _save_result(data: Dict[str, Any], tier: str, user_id: str, topic: str) -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = _result_path(tier, user_id, topic)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── FCR Metrics ───────────────────────────────────────────────────────────────

def _compute_fcr_metrics(
    run_result: Dict[str, Any],
    judge_model: str,
    judge_api_key: str,
    delay: float,
) -> List[Dict[str, Any]]:
    """Compute feedback compliance for each regeneration round."""
    rounds = run_result.get("rounds", [])
    fcr_results = []
    prev_example = run_result.get("initial_example", "")

    for r in rounds:
        if r.get("round", 0) == 0:
            continue
        feedback = r.get("feedback_given", "")
        new_example = r.get("example", "")

        # Only score if there was a regeneration (new example available)
        if not new_example or not prev_example:
            continue

        compliance = judge_feedback_compliance(
            original_example=prev_example,
            regenerated_example=new_example,
            feedback_given=feedback,
            topic=run_result.get("topic", ""),
            model=judge_model,
            api_key=judge_api_key,
        )
        fcr_results.append({
            "round": r["round"],
            "feedback_given": feedback,
            "compliance": compliance,
        })
        prev_example = new_example
        time.sleep(delay)

    return fcr_results


# ── Main Loop ─────────────────────────────────────────────────────────────────

def _pairwise_result_path(comparison: str, user_id: str, topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")
    return os.path.join(RESULTS_DIR, f"pairwise_{comparison}__{user_id}__{slug}.json")


def _run_pairwise_pass(
    profiles: List[Dict[str, Any]],
    topics: List[Dict[str, Any]],
    judge_model: str,
    judge_api_key: str,
    judge_delay: float,
    dry_run: bool,
) -> None:
    """
    PF-focused pairwise evaluation for warm users (start_mode='warm').
    Comparisons: T1 vs T2, T2 vs T3.
    Warm users are those with start_mode='warm'; cold users are skipped.
    """
    comparisons = [("t1", "t2"), ("t2", "t3")]
    warm_profiles = [p for p in profiles if p.get("start_mode") == "warm"]

    if not warm_profiles:
        print("\n[Pairwise] No warm users in selection — skipping pairwise pass.")
        return

    print(f"\n{'='*60}")
    print(f"PF Pairwise Pass | Warm users: {len(warm_profiles)} | Topics: {len(topics)}")
    print(f"Comparisons: {[f'{a} vs {b}' for a,b in comparisons]}")
    print(f"{'='*60}\n")

    for tier_a, tier_b in comparisons:
        label = f"{tier_a}_vs_{tier_b}"
        for profile in warm_profiles:
            user_id = profile["user_id"]
            # Load stored patterns for this user (warm users have seeded patterns)
            try:
                patterns_data = load_learning_patterns(user_id)
                stored_patterns = patterns_data.get("patterns", [])
            except Exception:
                stored_patterns = []

            for topic_info in topics:
                topic = topic_info["topic"]
                out_path = _pairwise_result_path(label, user_id, topic)
                if os.path.exists(out_path):
                    print(f"  [SKIP cached] {label} | {user_id} | {topic[:40]}")
                    continue

                print(f"  {label} | {user_id} | {topic[:40]} ...", flush=True)

                if dry_run:
                    print(f"    [DRY RUN] would compare {tier_a} vs {tier_b}")
                    continue

                # Load the final examples from saved tier results
                path_a = _result_path(tier_a, user_id, topic)
                path_b = _result_path(tier_b, user_id, topic)
                if not os.path.exists(path_a) or not os.path.exists(path_b):
                    print(f"    [SKIP] missing result files for {tier_a} or {tier_b}")
                    continue

                with open(path_a, encoding="utf-8") as f:
                    rec_a = json.load(f)
                with open(path_b, encoding="utf-8") as f:
                    rec_b = json.load(f)

                ex_a = rec_a.get("run", {}).get("final_example") or rec_a.get("run", {}).get("initial_example", "")
                ex_b = rec_b.get("run", {}).get("final_example") or rec_b.get("run", {}).get("initial_example", "")

                if not ex_a or not ex_b:
                    print(f"    [SKIP] empty example in {tier_a} or {tier_b}")
                    continue

                time.sleep(judge_delay)
                result = judge_pairwise_pf(
                    example_a=ex_a,
                    example_b=ex_b,
                    user_profile=profile,
                    topic=topic,
                    stored_patterns=stored_patterns,
                    model=judge_model,
                    api_key=judge_api_key,
                )
                record = {
                    "comparison": label,
                    "tier_a": tier_a,
                    "tier_b": tier_b,
                    "user_id": user_id,
                    "topic": topic,
                    "domain": topic_info["domain"],
                    "start_mode": profile.get("start_mode"),
                    "stored_patterns_count": len(stored_patterns),
                    "result": result,
                    "timestamp": datetime.now().isoformat(),
                }
                os.makedirs(RESULTS_DIR, exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(record, f, indent=2)
                print(f"    Winner: {result.get('final_winner')} | Saved: {out_path}")
                time.sleep(judge_delay)

    print(f"\nPairwise pass complete.")


def _instruction_specificity_path(tier: str, user_id: str, topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")
    return os.path.join(RESULTS_DIR, f"instruction_specificity__{tier}__{user_id}__{slug}.json")


def _compute_decision_accuracy(rounds: list, user_id: str) -> Dict[str, Any]:
    """
    Compare agent actions in rounds against ground truth expected decisions.
    Excludes rounds with None expected decision (ambiguous cases like A2).
    """
    correct = 0
    total = 0
    details = []
    for r in rounds:
        round_num = r.get("round", 0)
        if round_num == 0:
            continue
        expected = get_expected_decision(user_id, round_num)
        actual = r.get("agent_action")
        if expected is None:
            details.append({"round": round_num, "expected": None, "actual": actual, "excluded": True})
            continue
        match = (actual == expected)
        correct += int(match)
        total += 1
        details.append({"round": round_num, "expected": expected, "actual": actual, "correct": match})
    return {
        "correct": correct,
        "total": total,
        "accuracy": correct / total if total > 0 else None,
        "details": details,
    }


def _compute_pattern_selectivity(rounds: list) -> Dict[str, Any]:
    """
    Check flag_pattern invocation:
    - Round 3 (FP): should invoke flag_pattern → True Positive
    - Round 2 (F3): should NOT invoke flag_pattern → if it does, False Positive
    """
    round2_action = next((r.get("agent_action") for r in rounds if r.get("round") == 2), None)
    round3_action = next((r.get("agent_action") for r in rounds if r.get("round") == 3), None)

    tp = round3_action == "flag_pattern"
    fp = round2_action == "flag_pattern"

    return {
        "round2_action": round2_action,
        "round3_action": round3_action,
        "flag_on_fp_round": tp,      # True Positive — flagged on stable-trait message
        "flag_on_f3_round": fp,      # False Positive — incorrectly flagged on positive close
    }


def run_evaluation(
    tiers: List[str],
    user_indices: List[int],
    topic_indices: List[int],
    provider: str,
    judge_model: str,
    judge_api_key: str,
    secondary_model: str,
    secondary_api_key: str,
    delay: float,
    judge_delay: float,
    dry_run: bool,
    run_pairwise: bool,
    run_tag: str = "",
) -> None:
    _set_results_dir(run_tag)
    completed = _load_checkpoint()
    profiles = [SYNTHETIC_PROFILES[i] for i in user_indices]
    topics = [TOPICS[i] for i in topic_indices]

    total = len(tiers) * len(profiles) * len(topics)
    done = 0

    print(f"\n{'='*60}")
    print(f"AdaCraft Ablation Evaluation")
    tag_label = f" [{run_tag}]" if run_tag else ""
    print(f"Tiers: {tiers} | Users: {len(profiles)} | Topics: {len(topics)}{tag_label}")
    print(f"Generator: {provider} | Judge: {judge_model}")
    print(f"Results dir: {RESULTS_DIR}")
    print(f"Total cells: {total} | Already completed: {len(completed)}")
    print(f"Dry run: {dry_run}")
    print(f"{'='*60}\n")

    for tier in tiers:
        reset_manager()  # fresh manager per tier
        runner = TIER_RUNNERS[tier]

        for profile in profiles:
            user_id = profile["user_id"]

            for topic_info in topics:
                topic = topic_info["topic"]
                key = _result_key(tier, user_id, topic)
                done += 1

                if key in completed:
                    print(f"[{done}/{total}] SKIP (cached) {key}")
                    continue

                print(f"[{done}/{total}] Running {key} ...", flush=True)

                if dry_run:
                    print(f"  [DRY RUN] Would run {tier} for {user_id} / {topic}")
                    completed.add(key)
                    continue

                # ── Run tier ──────────────────────────────────────────────
                try:
                    run_result = runner(profile, topic, provider=provider, delay_seconds=delay)
                except Exception as e:
                    print(f"  ERROR running tier: {e}")
                    run_result = {"error": str(e), "rounds": [], "initial_example": ""}

                if run_result.get("error"):
                    print(f"  Run error: {run_result['error']}")

                # ── Judge initial example ─────────────────────────────────
                initial_example = run_result.get("initial_example", "")
                final_example = run_result.get("final_example", initial_example)

                initial_judgment = {}
                final_judgment = {}

                if initial_example:
                    time.sleep(judge_delay)
                    initial_judgment = judge_example(
                        example_text=initial_example,
                        user_profile=profile,
                        topic=topic,
                        model=judge_model,
                        api_key=judge_api_key,
                        secondary_model=secondary_model,
                        secondary_api_key=secondary_api_key,
                    )
                    print(f"  Initial composite: {initial_judgment.get('composite')}")

                # ── FCR metrics (T3 only) ─────────────────────────────────
                fcr_results = []
                if tier == "t3" and not run_result.get("error"):
                    fcr_results = _compute_fcr_metrics(
                        run_result, judge_model, judge_api_key, judge_delay
                    )

                # ── Per-round PF scoring (T3 only — for PF trajectory) ────
                # Round 0 reuses initial_judgment (no extra call).
                # Rounds 1+ are judged fresh only if a new example was generated.
                # The round-1 judgment is also stored as final_judgment when
                # final_example == round-1 example, avoiding a duplicate API call.
                round_pf_scores = []
                if tier == "t3" and not run_result.get("error"):
                    for r in run_result.get("rounds", []):
                        ex = r.get("example", "")
                        if not ex:
                            continue
                        round_num = r["round"]
                        if round_num == 0 and initial_judgment:
                            # Reuse already-computed judgment for round 0
                            rj = initial_judgment
                        else:
                            time.sleep(judge_delay)
                            rj = judge_example(
                                example_text=ex,
                                user_profile=profile,
                                topic=topic,
                                model=judge_model,
                                api_key=judge_api_key,
                            )
                            # If this is the round that produced the final example,
                            # store it so final_judgment can reuse it without a
                            # second API call.
                            if ex == final_example:
                                final_judgment = rj
                                print(f"  Final composite:   {final_judgment.get('composite')} (reused from round {round_num})")
                        round_pf_scores.append({
                            "round": round_num,
                            "pf_score": rj.get("scores", {}).get("PF"),
                            "composite": rj.get("composite"),
                            "agent_action": r.get("agent_action"),
                        })

                # ── Final judgment (non-T3 tiers, or T3 where round loop
                #    didn't cover final_example — e.g. error paths) ──────────
                if final_example and final_example != initial_example and not final_judgment:
                    time.sleep(judge_delay)
                    final_judgment = judge_example(
                        example_text=final_example,
                        user_profile=profile,
                        topic=topic,
                        model=judge_model,
                        api_key=judge_api_key,
                        secondary_model=secondary_model,
                        secondary_api_key=secondary_api_key,
                    )
                    print(f"  Final composite:   {final_judgment.get('composite')}")

                # ── Decision accuracy + pattern selectivity (T3 only) ──────
                decision_accuracy = {}
                pattern_selectivity = {}
                if tier == "t3":
                    rounds = run_result.get("rounds", [])
                    decision_accuracy = _compute_decision_accuracy(rounds, user_id)
                    pattern_selectivity = _compute_pattern_selectivity(rounds)

                # ── Instruction specificity (T2 only) ─────────────────────
                instruction_specificity = {}
                if tier == "t2":
                    ctx_instruction = run_result.get("context_instruction", "") or ""
                    if ctx_instruction:
                        try:
                            patterns_data = load_learning_patterns(user_id)
                            stored_patterns = patterns_data.get("patterns", [])
                        except Exception:
                            stored_patterns = []
                        try:
                            insights_data = load_accept_insights(user_id)
                            accept_insights_list = insights_data.get("insights", [])
                        except Exception:
                            accept_insights_list = []
                        time.sleep(judge_delay)
                        instruction_specificity = judge_instruction_specificity(
                            context_instruction=ctx_instruction,
                            user_profile=profile,
                            stored_patterns=stored_patterns,
                            accept_insights=accept_insights_list,
                            topic=topic,
                            model=judge_model,
                            api_key=judge_api_key,
                        )
                        spec_record = {
                            "tier": tier,
                            "user_id": user_id,
                            "topic": topic,
                            "start_mode": profile.get("start_mode"),
                            "context_instruction": ctx_instruction,
                            "stored_patterns_count": len(stored_patterns),
                            "judgment": instruction_specificity,
                            "timestamp": datetime.now().isoformat(),
                        }
                        spec_path = _instruction_specificity_path(tier, user_id, topic)
                        with open(spec_path, "w") as f:
                            json.dump(spec_record, f, indent=2)
                        print(f"  Instruction specificity: {instruction_specificity.get('specificity_score')}")

                # ── Save result ───────────────────────────────────────────
                result_record = {
                    "key": key,
                    "tier": tier,
                    "user_id": user_id,
                    "topic": topic,
                    "domain": topic_info["domain"],
                    "profile": {k: v for k, v in profile.items() if not k.startswith("_")},
                    "run": run_result,
                    "initial_judgment": initial_judgment,
                    "final_judgment": final_judgment,
                    "fcr_results": fcr_results,
                    "context_instruction": run_result.get("context_instruction"),
                    "round_pf_scores": round_pf_scores,
                    "decision_accuracy": decision_accuracy,
                    "pattern_selectivity": pattern_selectivity,
                    "instruction_specificity": instruction_specificity,
                    "timestamp": datetime.now().isoformat(),
                }
                _save_result(result_record, tier, user_id, topic)
                completed.add(key)
                _save_checkpoint(completed)

                print(f"  Saved: {_result_path(tier, user_id, topic)}")
                time.sleep(delay)

    print(f"\nEvaluation complete. {len(completed)} cells in checkpoint.")

    # ── Pairwise PF pass (warm users, T1 vs T2, T2 vs T3) ────────────────────
    if run_pairwise:
        _run_pairwise_pass(
            profiles=profiles,
            topics=topics,
            judge_model=judge_model,
            judge_api_key=judge_api_key,
            judge_delay=judge_delay,
            dry_run=dry_run,
        )


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args():
    parser = argparse.ArgumentParser(description="AdaCraft Ablation Evaluation Runner")
    parser.add_argument("--tiers", nargs="+", default=["t0", "t1", "t2", "t3"],
                        choices=["t0", "t1", "t2", "t3"])
    parser.add_argument("--users", default="0-7",
                        help="User index range, e.g. '0-7' or '0,4,6'")
    parser.add_argument("--topics", default="0-3",
                        help="Topic index range, e.g. '0-3' or '0,2'")
    parser.add_argument("--provider", default="openai",
                        help="LLM provider for generation: openai|openrouter")
    parser.add_argument("--judge-model", default="gpt-4.1-nano",
                        help="OpenAI model for judging")
    parser.add_argument("--judge-api-key", default=None,
                        help="OpenAI API key for judge (falls back to OPENAI_API_KEY env var)")
    parser.add_argument("--secondary-model", default=None,
                        help="Secondary judge model. Use 'openrouter:<model>' for OpenRouter "
                             "(e.g. 'openrouter:meta-llama/llama-3.3-70b-instruct'). "
                             "Set to '' or omit to disable.")
    parser.add_argument("--secondary-api-key", default=None,
                        help="API key for secondary judge (OpenRouter key if using openrouter: prefix). "
                             "Falls back to OPENROUTER_API_KEY env var.")
    parser.add_argument("--pairwise", action="store_true",
                        help="Run PF-focused pairwise pass (T1 vs T2, T2 vs T3) for warm users "
                             "after the main tier loop.")
    parser.add_argument("--delay", type=float, default=0.0,
                        help="Seconds between generation calls")
    parser.add_argument("--judge-delay", type=float, default=0.0,
                        help="Seconds between judge calls")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would run without calling LLMs")
    parser.add_argument("--run-tag", default="",
                        help="Tag to namespace results in eval/results/<tag>/. "
                             "Use different tags for different generator runs "
                             "(e.g. 'gpt4nano', 'deepseek') to avoid overwriting.")
    return parser.parse_args()


def _parse_indices(spec: str, max_val: int) -> List[int]:
    """Parse '0-9', '0,2,4', or '3' into a list of ints."""
    if "-" in spec and "," not in spec:
        start, end = spec.split("-")
        return list(range(int(start), int(end) + 1))
    elif "," in spec:
        return [int(x) for x in spec.split(",")]
    else:
        return [int(spec)]


if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

    args = _parse_args()

    judge_api_key = args.judge_api_key or os.environ.get("OPENAI_API_KEY")
    if not judge_api_key and not args.dry_run:
        print("ERROR: --judge-api-key or OPENAI_API_KEY env var required for judging.")
        sys.exit(1)

    secondary_api_key = args.secondary_api_key or os.environ.get("OPENROUTER_JUDGE_API_KEY")

    user_indices = _parse_indices(args.users, len(SYNTHETIC_PROFILES) - 1)
    topic_indices = _parse_indices(args.topics, len(TOPICS) - 1)

    run_evaluation(
        tiers=args.tiers,
        user_indices=user_indices,
        topic_indices=topic_indices,
        provider=args.provider,
        judge_model=args.judge_model,
        judge_api_key=judge_api_key,
        secondary_model=args.secondary_model or None,
        secondary_api_key=secondary_api_key,
        delay=args.delay,
        judge_delay=args.judge_delay,
        dry_run=args.dry_run,
        run_pairwise=args.pairwise,
        run_tag=args.run_tag,
    )
