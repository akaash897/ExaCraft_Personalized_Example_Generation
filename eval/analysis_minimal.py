#!/usr/bin/env python3
"""
Minimal Analysis: Ablation + Convergence Metrics (FCR, LUR, PPU)

Loads scores_*.json and computes:
  - Ablation Results: Mean scores by tier (T0-T3)
  - FCR: Feedback Compliance Rate (T3 only)
  - LUR: Loop Utilization Rate (T3 only)
  - PPU: Pattern Persistence Utilization (warm vs cold start)

Usage:
  python eval/analysis_minimal.py [--results-dir eval/results/deepseek] [--provider deepseek]
"""

import sys
import os
import json
import glob
import argparse
from collections import defaultdict
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.synthetic_profiles import get_feedback_battery_type

TIERS = ["t0", "t1", "t2", "t3"]
TIER_LABELS = {"t0": "T0 Generic", "t1": "T1 +Profile", "t2": "T2 +Context", "t3": "T3 Full"}
AXES = ["PF", "CC", "CA", "PC", "DA"]
AXIS_WEIGHTS = {"PF": 0.20, "CC": 0.20, "CA": 0.30, "PC": 0.20, "DA": 0.10}


# ── Load Results ──────────────────────────────────────────────────────────────

def load_results(results_dir: str) -> List[Dict[str, Any]]:
    """Load all scores_*.json files from results_dir."""
    pattern = os.path.join(results_dir, "scores_*.json")
    files = glob.glob(pattern)
    records = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            try:
                records.append(json.load(f))
            except Exception as e:
                print(f"  Skipping {path}: {e}")
    print(f"[OK] Loaded {len(records)} score records from {results_dir}")
    return records


def _get_composite(record: Dict, judgment_key: str = "initial_judgment") -> Optional[float]:
    j = record.get(judgment_key, {})
    return j.get("composite")


def _get_scores(record: Dict, judgment_key: str = "initial_judgment") -> Optional[Dict]:
    j = record.get(judgment_key, {})
    return j.get("scores")


# ── Ablation Results ──────────────────────────────────────────────────────────

def compute_ablation(records: List[Dict]) -> Dict[str, Dict[str, float]]:
    """
    Compute mean scores by tier.

    Returns: {
        "t0": {"PF": float, "CC": float, "CA": float, "PC": float, "DA": float, "composite": float},
        ...
    }
    """
    tier_scores = {t: {ax: [] for ax in AXES} for t in TIERS}
    tier_composites = {t: [] for t in TIERS}

    for r in records:
        tier = r.get("tier")
        if tier not in TIERS:
            continue

        scores = _get_scores(r, "initial_judgment")
        composite = _get_composite(r, "initial_judgment")

        if scores:
            for ax in AXES:
                if ax in scores:
                    tier_scores[tier][ax].append(scores[ax])

        if composite is not None:
            tier_composites[tier].append(composite)

    # Compute means
    result = {}
    for tier in TIERS:
        result[tier] = {}
        for ax in AXES:
            vals = tier_scores[tier][ax]
            result[tier][ax] = round(sum(vals) / len(vals), 2) if vals else None

        comp_vals = tier_composites[tier]
        result[tier]["composite"] = round(sum(comp_vals) / len(comp_vals), 3) if comp_vals else None
        result[tier]["n"] = len(comp_vals)

    return result


# ── Convergence Metrics ───────────────────────────────────────────────────────

def compute_fcr(records: List[Dict]) -> Dict:
    """
    Feedback Compliance Rate: Proportion of regenerations with compliance_score >= 3/4.
    Only uses T3 records with fcr_results.
    """
    t3 = [r for r in records if r.get("tier") == "t3"]

    buckets = {"easy": [], "adversarial": [], "all": []}
    for r in t3:
        for fc in r.get("fcr_results", []):
            score = fc.get("compliance", {}).get("compliance_score")
            if score is None:
                continue
            battery = get_feedback_battery_type(fc.get("feedback_given", ""))
            buckets[battery].append(score)
            buckets["all"].append(score)

    def summarise(scores: List[int]) -> Dict:
        if not scores:
            return {"n": 0, "fcr_3": None, "fcr_4": None, "mean": None}
        return {
            "n": len(scores),
            "fcr_3": round(sum(1 for s in scores if s >= 3) / len(scores), 3),
            "fcr_4": round(sum(1 for s in scores if s >= 4) / len(scores), 3),
            "mean": round(sum(scores) / len(scores), 3),
        }

    return {
        "easy": summarise(buckets["easy"]),
        "adversarial": summarise(buckets["adversarial"]),
        "overall": summarise(buckets["all"]),
    }


def compute_lur(records: List[Dict]) -> Dict:
    """
    Loop Utilization Rate: Fraction of T3 sessions that triggered >= 1 regeneration.
    """
    t3 = [r for r in records if r.get("tier") == "t3"]
    if not t3:
        return {"n": 0, "lur": None}

    def _had_regen(r: Dict) -> bool:
        return any(
            rd.get("status") == "awaiting_feedback"
            for rd in r.get("run", {}).get("rounds", [])
            if rd.get("round", 0) > 0
        )

    def _battery(r: Dict) -> str:
        return "adversarial" if r.get("profile", {}).get("start_mode") == "warm" else "easy"

    buckets = {"easy": [], "adversarial": [], "all": []}
    for r in t3:
        regen = _had_regen(r)
        b = _battery(r)
        buckets[b].append(regen)
        buckets["all"].append(regen)

    def summarise(vals: List[bool]) -> Dict:
        if not vals:
            return {"n": 0, "triggered": 0, "lur": None}
        return {
            "n": len(vals),
            "triggered": sum(vals),
            "lur": round(sum(vals) / len(vals), 3),
        }

    return {
        "easy": summarise(buckets["easy"]),
        "adversarial": summarise(buckets["adversarial"]),
        "overall": summarise(buckets["all"]),
    }


def compute_ppu(records: List[Dict]) -> Dict:
    """
    Pattern Persistence Utilization: PF delta between warm T3 and warm T1 initial examples.
    Measures whether stored patterns improve personalization at generation time.
    """
    warm_t3 = [r for r in records if r.get("tier") == "t3" and r.get("profile", {}).get("start_mode") == "warm"]
    warm_t1 = [r for r in records if r.get("tier") == "t1" and r.get("profile", {}).get("start_mode") == "warm"]
    cold_t3 = [r for r in records if r.get("tier") == "t3" and r.get("profile", {}).get("start_mode") == "cold"]

    def _mean_pf(recs: List[Dict]) -> Optional[float]:
        scores = [
            _get_scores(r, "initial_judgment").get("PF")
            for r in recs
            if _get_scores(r, "initial_judgment")
        ]
        scores = [s for s in scores if s is not None]
        return round(sum(scores) / len(scores), 3) if scores else None

    warm_t3_pf = _mean_pf(warm_t3)
    warm_t1_pf = _mean_pf(warm_t1)
    cold_t3_pf = _mean_pf(cold_t3)

    delta = round(warm_t3_pf - warm_t1_pf, 3) if (warm_t3_pf is not None and warm_t1_pf is not None) else None

    return {
        "n_warm_t3": len(warm_t3),
        "n_warm_t1": len(warm_t1),
        "n_cold_t3": len(cold_t3),
        "warm_t3_pf": warm_t3_pf,
        "warm_t1_pf": warm_t1_pf,
        "cold_t3_pf": cold_t3_pf,
        "delta_pf": delta,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main(results_dir: str, provider: str) -> None:
    """Load results, compute metrics, and print to console + JSON."""

    print(f"\n{'='*70}")
    print(f"ANALYSIS: {provider.upper()}")
    print(f"{'='*70}\n")

    records = load_results(results_dir)

    # Ablation
    print("\n[1] Ablation Results (Tier Means)")
    print("-" * 70)
    ablation = compute_ablation(records)

    for tier in TIERS:
        result = ablation[tier]
        pf = result.get("PF")
        cc = result.get("CC")
        ca = result.get("CA")
        pc = result.get("PC")
        da = result.get("DA")
        comp = result.get("composite")
        n = result.get("n")
        print(f"{TIER_LABELS[tier]:<16} PF={pf:>5} CC={cc:>5} CA={ca:>5} PC={pc:>5} DA={da:>5} | Composite={comp:>6} (n={n})")

    # Compute deltas
    print("\nTier Deltas (Delta from T0):")
    if ablation["t0"]["composite"]:
        for tier in TIERS[1:]:
            delta = round(ablation[tier]["composite"] - ablation["t0"]["composite"], 3)
            print(f"  T0 -> {tier}: +{delta}")

    # FCR
    print("\n[2] Feedback Compliance Rate (T3)")
    print("-" * 70)
    fcr = compute_fcr(records)
    for battery_type in ["easy", "adversarial", "overall"]:
        result = fcr[battery_type]
        print(f"{battery_type:<12} FCR@3={result.get('fcr_3')} FCR@4={result.get('fcr_4')} (n={result.get('n')})")

    # LUR
    print("\n[3] Loop Utilization Rate (T3)")
    print("-" * 70)
    lur = compute_lur(records)
    for battery_type in ["easy", "adversarial", "overall"]:
        result = lur[battery_type]
        print(f"{battery_type:<12} LUR={result.get('lur')} (triggered={result.get('triggered')}/{result.get('n')})")

    # PPU
    print("\n[4] Pattern Persistence Utilization")
    print("-" * 70)
    ppu = compute_ppu(records)
    print(f"Warm T3 initial PF (n={ppu['n_warm_t3']}):  {ppu['warm_t3_pf']}")
    print(f"Warm T1 initial PF (n={ppu['n_warm_t1']}):  {ppu['warm_t1_pf']}")
    print(f"Cold T3 initial PF (n={ppu['n_cold_t3']}):  {ppu['cold_t3_pf']}")
    print(f"Delta PF (Warm T3 - Warm T1): {ppu['delta_pf']}")

    # Save results
    output_file = os.path.join(results_dir, f"analysis_{provider}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "provider": provider,
            "ablation": ablation,
            "fcr": fcr,
            "lur": lur,
            "ppu": ppu,
        }, f, indent=2)
    print(f"\n[OK] Results saved to {output_file}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Minimal evaluation analysis")
    parser.add_argument("--results-dir", default="eval/results/deepseek", help="Results directory")
    parser.add_argument("--provider", default="deepseek", help="Provider name for output")
    args = parser.parse_args()

    main(args.results_dir, args.provider)
