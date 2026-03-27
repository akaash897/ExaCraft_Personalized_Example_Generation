"""
LLM Judge
G-Eval + Prometheus 2 pattern for scoring generated examples on 5 axes.
Primary judge: GPT-4.1-nano. Secondary judge (20% subsample): Llama 3.3 70B via OpenRouter.

Axes:
  PF  Personalization Fidelity   weight 0.20
  CC  Complexity Calibration     weight 0.20
  CA  Conceptual Accuracy        weight 0.30
  PC  Pedagogical Clarity        weight 0.20
  DA  Domain Appropriateness     weight 0.10

Composite = 0.20·PF + 0.20·CC + 0.30·CA + 0.20·PC + 0.10·DA

OpenRouter usage:
  Pass model as "openrouter:<model_id>", e.g. "openrouter:meta-llama/llama-3.3-70b-instruct"
  Requires OPENROUTER_API_KEY env var or explicit secondary_api_key argument.
  API docs: https://openrouter.ai/docs

Ollama usage (legacy):
  Ollama exposes an OpenAI-compatible API at http://localhost:11434/v1.
  Pull your model first: `ollama pull qwen3.5:2b`
"""

import re
import json
import time
from typing import Dict, Any, Optional, List, Tuple

from openai import OpenAI

OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_DEFAULT_MODEL = "qwen3.5:2b"  # change to llama3.2:3b, phi3:mini, etc. if preferred

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct"

# ── Weights ───────────────────────────────────────────────────────────────────

AXIS_WEIGHTS = {
    "PF": 0.20,
    "CC": 0.20,
    "CA": 0.30,
    "PC": 0.20,
    "DA": 0.10,
}

# ── Rubric Definitions (Prometheus 2 style) ───────────────────────────────────

RUBRIC = """
EVALUATION AXES AND RUBRIC (score 1-5 for each):

[PF] PERSONALIZATION FIDELITY — Does the example reflect the user's actual profile?
  5: Example is clearly tailored — uses name/location/profession, matches learning style, analogies are domain-specific.
  4: Mostly personalized — 2-3 profile elements present but not all.
  3: Weakly personalized — generic scenario with token name/location insertion.
  2: Barely personalized — one profile element mentioned, rest generic.
  1: No personalization — could have been generated for any user.

[CC] COMPLEXITY CALIBRATION — Does the depth match the user's stated complexity level?
  5: Complexity perfectly calibrated — language, depth, and formulas match the requested level exactly.
  4: Mostly calibrated — one minor level mismatch (slightly too hard/easy).
  3: Partially calibrated — notable mismatch but concept is still accessible.
  2: Poor calibration — content is substantially above/below the learner's level.
  1: No calibration — complexity completely inappropriate for the learner.

[CA] CONCEPTUAL ACCURACY — Is the factual/scientific content correct?
  5: Fully accurate — all facts, formulas, and definitions are correct.
  4: Mostly accurate — one minor error or imprecision that doesn't mislead.
  3: Partially accurate — one significant error but core concept is sound.
  2: Mostly inaccurate — multiple factual errors that could mislead the learner.
  1: Factually wrong — central claim is incorrect.

[PC] PEDAGOGICAL CLARITY — Is the example structured for learning?
  5: Excellent — clear structure, smooth flow, concept-to-example bridge is explicit, insight is memorable.
  4: Good — clear but one section (e.g., insight or bridge) is underdeveloped.
  3: Adequate — readable but lacks explicit concept-example bridge or memorable takeaway.
  2: Poor — disorganized or too dense; hard to follow as a learner.
  1: Unstructured — no clear format; reads like raw text, not a teaching example.

[DA] DOMAIN APPROPRIATENESS — Are analogies and framing appropriate for the topic's domain?
  5: Perfectly domain-appropriate — analogies, vocabulary, and framing match the topic's field.
  4: Mostly appropriate — one analogy that's slightly off-domain but not harmful.
  3: Mixed — some appropriate framing with one off-domain element (e.g., code in a biology example).
  2: Off-domain — analogies are mostly from the wrong domain.
  1: Domain mismatch — framing is entirely inappropriate (e.g., coding tutorial for a history topic).
"""

SYSTEM_PROMPT = """You are an expert evaluator of personalized educational content.
Your task is to evaluate a generated educational example on five axes using a 1-5 scale.

You MUST follow this procedure strictly:
1. For each axis, write 1-2 sentences of reasoning BEFORE giving the score.
2. Then output the score in the format: AXIS_SCORE: [1-5]
3. Do not skip axes. Do not output scores without prior reasoning.
4. After all axes, output the scores in a JSON block.

Bias mitigations:
- Do not favor longer examples — verbosity is NOT a virtue.
- Do not reward examples that merely repeat profile fields without integrating them.
- Judge domain appropriateness strictly — code snippets in non-CS topics should be penalized.
"""

# ── Score Parsing ─────────────────────────────────────────────────────────────

def _parse_scores(text: str) -> Dict[str, int]:
    """Extract axis scores from judge response using regex fallback + JSON block."""
    scores = {}

    # Try JSON block first
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        try:
            raw = json.loads(json_match.group(1))
            for axis in AXIS_WEIGHTS:
                key_candidates = [axis, f"{axis}_SCORE", f"{axis}_score", axis.lower()]
                for k in key_candidates:
                    if k in raw:
                        scores[axis] = int(raw[k])
                        break
        except Exception:
            pass

    # Regex fallback for any missing axes
    for axis in AXIS_WEIGHTS:
        if axis not in scores:
            pattern = rf"{axis}[_\s]SCORE[:\s]+([1-5])"
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                scores[axis] = int(m.group(1))

    return scores


def _compute_composite(scores: Dict[str, int]) -> Optional[float]:
    if len(scores) < len(AXIS_WEIGHTS):
        return None
    return sum(AXIS_WEIGHTS[ax] * scores[ax] for ax in AXIS_WEIGHTS)


# ── Judge API Calls ───────────────────────────────────────────────────────────

def _call_openai_judge(
    prompt: str,
    model: str = "gpt-4o",
    api_key: str = None,
    temperature: float = 0.0,
    max_retries: int = 3,
) -> str:
    """Call GPT-4.1-mini (or any OpenAI model) as judge."""
    client = OpenAI(api_key=api_key, timeout=60.0)
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"Judge API call failed after {max_retries} attempts: {e}")


def _call_ollama_judge(
    prompt: str,
    model: str = OLLAMA_DEFAULT_MODEL,
    temperature: float = 0.0,
    max_retries: int = 3,
) -> str:
    """
    Call a local Ollama model as judge via its OpenAI-compatible API.
    Requires Ollama running locally: https://ollama.com
    Pull model first: ollama pull mistral
    """
    # api_key="ollama" is a dummy value — Ollama doesn't validate it
    client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama", timeout=60.0)
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                timeout=60,
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise RuntimeError(
                    f"Ollama judge call failed after {max_retries} attempts: {e}\n"
                    f"Is Ollama running? Try: ollama serve"
                )


def _call_openrouter_judge(
    prompt: str,
    model: str = OPENROUTER_DEFAULT_MODEL,
    api_key: str = None,
    temperature: float = 0.0,
    max_retries: int = 3,
) -> str:
    """Call any model via OpenRouter's OpenAI-compatible API."""
    import os
    key = api_key or os.environ.get("OPENROUTER_JUDGE_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError(
            "OpenRouter API key required. Pass secondary_api_key or set OPENROUTER_JUDGE_API_KEY env var."
        )
    client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=key,
        timeout=60.0,
        default_headers={"HTTP-Referer": "https://exacraft.local", "X-Title": "ExaCraft Eval"},
    )
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"OpenRouter judge call failed after {max_retries} attempts: {e}")


def _call_judge(
    prompt: str,
    model: str,
    api_key: str = None,
    temperature: float = 0.0,
) -> str:
    """Route to OpenRouter, Ollama, or OpenAI based on model prefix/name."""
    if model.startswith("openrouter:"):
        or_model = model[len("openrouter:"):]
        return _call_openrouter_judge(prompt, model=or_model, api_key=api_key, temperature=temperature)
    if model.startswith("ollama:"):
        ollama_model = model[len("ollama:"):]
        return _call_ollama_judge(prompt, model=ollama_model, temperature=temperature)
    # Check if it's a bare Ollama model name (no API key needed → use Ollama)
    known_ollama_models = {"mistral", "llama3.2", "llama3.2:3b", "phi3", "phi3:mini",
                           "qwen2.5", "qwen2.5:3b", "qwen3.5", "qwen3.5:2b", "gemma2", "gemma2:2b", "llama3", "codellama"}
    base = model.split(":")[0]
    if base in known_ollama_models or not api_key:
        return _call_ollama_judge(prompt, model=model, temperature=temperature)
    return _call_openai_judge(prompt, model=model, api_key=api_key, temperature=temperature)


# ── Main Judge Functions ──────────────────────────────────────────────────────

def judge_example(
    example_text: str,
    user_profile: Dict[str, Any],
    topic: str,
    model: str = "gpt-4o",
    api_key: str = None,
    secondary_model: str = None,
    secondary_api_key: str = None,
    secondary_subsample_rate: float = 0.20,
) -> Dict[str, Any]:
    """
    Score a single example on all 5 axes.

    If secondary_model is set (e.g. "openrouter:meta-llama/llama-3.1-8b-instruct"),
    runs it on `secondary_subsample_rate` fraction of calls and appends secondary
    scores for inter-judge Cohen's κ computation in analysis.py.
    secondary_api_key: API key for the secondary judge (OpenRouter key if using openrouter: prefix).

    Returns:
        {
          "scores": {"PF": int, "CC": int, "CA": int, "PC": int, "DA": int},
          "composite": float,
          "reasoning": str,
          "model": str,
          "secondary": Optional[dict],
          "error": Optional[str]
        }
    """
    profile_str = json.dumps(
        {k: v for k, v in user_profile.items() if not k.startswith("_")},
        indent=2
    )

    prompt = f"""TOPIC: {topic}

USER PROFILE:
{profile_str}

EVALUATION RUBRIC:
{RUBRIC}

EXAMPLE TO EVALUATE:
\"\"\"
{example_text}
\"\"\"

Instructions:
- For EACH axis (PF, CC, CA, PC, DA), write 1-2 sentences of reasoning, then output: AXIS_SCORE: [1-5]
- After all axes, output your scores as:
```json
{{"PF": X, "CC": X, "CA": X, "PC": X, "DA": X}}
```
"""
    import random
    try:
        reasoning = _call_judge(prompt, model=model, api_key=api_key)
        scores = _parse_scores(reasoning)
        composite = _compute_composite(scores)
        result = {
            "scores": scores,
            "composite": composite,
            "reasoning": reasoning,
            "model": model,
            "error": None if len(scores) == len(AXIS_WEIGHTS) else "Incomplete scores parsed",
            "secondary": None,
        }

        # Secondary judge on subsample for inter-judge agreement
        if secondary_model and random.random() < secondary_subsample_rate:
            try:
                sec_reasoning = _call_judge(prompt, model=secondary_model, api_key=secondary_api_key)
                sec_scores = _parse_scores(sec_reasoning)
                result["secondary"] = {
                    "model": secondary_model,
                    "scores": sec_scores,
                    "composite": _compute_composite(sec_scores),
                    "reasoning": sec_reasoning,
                }
            except Exception as sec_e:
                result["secondary"] = {"error": str(sec_e), "model": secondary_model}

        return result
    except Exception as e:
        return {
            "scores": {},
            "composite": None,
            "reasoning": "",
            "model": model,
            "error": str(e),
            "secondary": None,
        }


def judge_pairwise(
    example_a: str,
    example_b: str,
    user_profile: Dict[str, Any],
    topic: str,
    model: str = "gpt-4o",
    api_key: str = None,
) -> Dict[str, Any]:
    """
    Pairwise comparison: which example is better for this user/topic?
    Runs both A>B and B>A orderings to mitigate position bias (MT-Bench).

    Returns:
        {
          "winner_ab": "A" | "B" | "tie",
          "winner_ba": "A" | "B" | "tie",
          "final_winner": "A" | "B" | "tie",
          "reasoning_ab": str,
          "reasoning_ba": str,
        }
    """
    profile_str = json.dumps(
        {k: v for k, v in user_profile.items() if not k.startswith("_")},
        indent=2
    )

    def _pairwise_prompt(first: str, second: str, label_first: str, label_second: str) -> str:
        return f"""TOPIC: {topic}
USER PROFILE:
{profile_str}

EVALUATION RUBRIC:
{RUBRIC}

You are comparing two educational examples for this user and topic.
Answer which is better overall considering PF, CC, CA, PC, DA.
Be concise. State your reasoning, then end with: WINNER: {label_first} | WINNER: {label_second} | WINNER: TIE

EXAMPLE {label_first}:
\"\"\"
{first}
\"\"\"

EXAMPLE {label_second}:
\"\"\"
{second}
\"\"\"

Reasoning (2-3 sentences), then WINNER: X
"""

    def _parse_winner(text: str, label_a: str, label_b: str) -> str:
        m = re.search(r"WINNER:\s*([A-Z]+)", text, re.IGNORECASE)
        if not m:
            return "tie"
        w = m.group(1).upper()
        if w == label_a:
            return "A"
        if w == label_b:
            return "B"
        return "tie"

    try:
        resp_ab = _call_judge(_pairwise_prompt(example_a, example_b, "A", "B"), model=model, api_key=api_key)
        winner_ab = _parse_winner(resp_ab, "A", "B")

        resp_ba = _call_judge(_pairwise_prompt(example_b, example_a, "B", "A"), model=model, api_key=api_key)
        winner_ba_raw = _parse_winner(resp_ba, "B", "A")
        # Flip: in BA ordering, "A" label is B and "B" label is A
        winner_ba = winner_ba_raw  # already parsed relative to original A/B

        # Aggregate
        votes = {"A": 0, "B": 0, "tie": 0}
        votes[winner_ab] += 1
        votes[winner_ba] += 1
        final = max(votes, key=votes.get)
        if votes["A"] == votes["B"]:
            final = "tie"

        return {
            "winner_ab": winner_ab,
            "winner_ba": winner_ba,
            "final_winner": final,
            "reasoning_ab": resp_ab,
            "reasoning_ba": resp_ba,
            "error": None,
        }
    except Exception as e:
        return {
            "winner_ab": None,
            "winner_ba": None,
            "final_winner": None,
            "reasoning_ab": "",
            "reasoning_ba": "",
            "error": str(e),
        }


def judge_pairwise_pf(
    example_a: str,
    example_b: str,
    user_profile: Dict[str, Any],
    topic: str,
    stored_patterns: List[Dict[str, Any]],
    model: str = "gpt-4o",
    api_key: str = None,
) -> Dict[str, Any]:
    """
    PF-focused pairwise: which example better reflects this user's learning history?
    Includes stored learning patterns in the prompt so the judge can assess PF discrimination.
    Runs both A>B and B>A orderings to mitigate position bias (MT-Bench).

    stored_patterns: list of pattern dicts from load_learning_patterns() — warm users only.

    Returns:
        {
          "winner_ab": "A" | "B" | "tie",
          "winner_ba": "A" | "B" | "tie",
          "final_winner": "A" | "B" | "tie",
          "reasoning_ab": str,
          "reasoning_ba": str,
          "error": Optional[str],
        }
    """
    profile_str = json.dumps(
        {k: v for k, v in user_profile.items() if not k.startswith("_")},
        indent=2
    )
    patterns_str = json.dumps(stored_patterns[-10:], indent=2) if stored_patterns else "None"

    def _pf_prompt(first: str, second: str, label_first: str, label_second: str) -> str:
        return f"""TOPIC: {topic}

USER PROFILE:
{profile_str}

USER'S STORED LEARNING PATTERNS (from prior feedback sessions):
{patterns_str}

TASK: You are evaluating Personalization Fidelity (PF) ONLY.
Determine which example better reflects this specific user's learning history,
preferences, and documented patterns above.

SCORING FOCUS — PF (Personalization Fidelity):
  5: Example clearly incorporates documented learning patterns (preferred style, noted struggles/mastery, domain analogy preferences).
  4: Example reflects most documented patterns but misses one.
  3: Example reflects profile fields (name/role) but ignores stored patterns.
  2: Example uses one profile field; stored patterns not reflected.
  1: Example is generic — no profile or pattern alignment.

Do NOT score on factual accuracy or pedagogy — PF only.
Write 2-3 sentences of reasoning referencing specific patterns, then end with:
WINNER: {label_first} | WINNER: {label_second} | WINNER: TIE

EXAMPLE {label_first}:
\"\"\"
{first}
\"\"\"

EXAMPLE {label_second}:
\"\"\"
{second}
\"\"\"

Reasoning (referencing stored patterns), then WINNER: X
"""

    def _parse_winner(text: str, label_a: str, label_b: str) -> str:
        m = re.search(r"WINNER:\s*([A-Z]+)", text, re.IGNORECASE)
        if not m:
            return "tie"
        w = m.group(1).upper()
        if w == label_a:
            return "A"
        if w == label_b:
            return "B"
        return "tie"

    try:
        resp_ab = _call_judge(_pf_prompt(example_a, example_b, "A", "B"), model=model, api_key=api_key)
        winner_ab = _parse_winner(resp_ab, "A", "B")

        resp_ba = _call_judge(_pf_prompt(example_b, example_a, "B", "A"), model=model, api_key=api_key)
        winner_ba = _parse_winner(resp_ba, "B", "A")

        votes = {"A": 0, "B": 0, "tie": 0}
        votes[winner_ab] += 1
        votes[winner_ba] += 1
        final = max(votes, key=votes.get)
        if votes["A"] == votes["B"]:
            final = "tie"

        return {
            "winner_ab": winner_ab,
            "winner_ba": winner_ba,
            "final_winner": final,
            "reasoning_ab": resp_ab,
            "reasoning_ba": resp_ba,
            "error": None,
        }
    except Exception as e:
        return {
            "winner_ab": None,
            "winner_ba": None,
            "final_winner": None,
            "reasoning_ab": "",
            "reasoning_ba": "",
            "error": str(e),
        }


def judge_feedback_compliance(
    original_example: str,
    regenerated_example: str,
    feedback_given: str,
    topic: str,
    model: str = "gpt-4o",
    api_key: str = None,
) -> Dict[str, Any]:
    """
    FCR: Did the regenerated example address the user's feedback critique?

    Returns:
        {
          "compliant": bool,
          "compliance_score": int (1-5),
          "reasoning": str,
          "error": Optional[str]
        }
    """
    prompt = f"""TOPIC: {topic}

USER FEEDBACK (critique of the original example):
\"{feedback_given}\"

ORIGINAL EXAMPLE:
\"\"\"
{original_example}
\"\"\"

REGENERATED EXAMPLE:
\"\"\"
{regenerated_example}
\"\"\"

Task: Evaluate whether the regenerated example correctly addresses the user's critique.

Score on a 1-5 scale:
  5: Fully addresses the feedback — the specific complaint is resolved.
  4: Mostly addressed — main point resolved but minor aspects missed.
  3: Partially addressed — some improvement but the core complaint remains.
  2: Barely addressed — superficial changes that don't resolve the complaint.
  1: Not addressed — the regenerated example ignores the feedback entirely.

Write 1-2 sentences of reasoning, then output:
COMPLIANCE_SCORE: [1-5]
COMPLIANT: YES | NO
"""
    try:
        response = _call_judge(prompt, model=model, api_key=api_key)
        score_match = re.search(r"COMPLIANCE_SCORE:\s*([1-5])", response)
        compliant_match = re.search(r"COMPLIANT:\s*(YES|NO)", response, re.IGNORECASE)

        score = int(score_match.group(1)) if score_match else None
        compliant = compliant_match.group(1).upper() == "YES" if compliant_match else (score >= 3 if score else None)

        return {
            "compliant": compliant,
            "compliance_score": score,
            "reasoning": response,
            "error": None,
        }
    except Exception as e:
        return {
            "compliant": None,
            "compliance_score": None,
            "reasoning": "",
            "error": str(e),
        }


def judge_instruction_specificity(
    context_instruction: str,
    user_profile: Dict[str, Any],
    stored_patterns: List[Dict[str, Any]],
    accept_insights: List[Dict[str, Any]],
    topic: str,
    model: str = "gpt-4o",
    api_key: str = None,
) -> Dict[str, Any]:
    """
    Rate the ContextManager's generated context instruction on specificity (1-5).

    Rubric:
      5: Synthesizes stored patterns into a targeted, actionable, example-specific directive.
      4: References specific patterns with a concrete directive.
      3: References patterns and gives a general directive.
      2: Mentions stored domain but gives no actionable directive.
      1: Restates profile fields only; no reference to stored patterns.

    Returns:
        {"specificity_score": int, "reasoning": str, "error": Optional[str]}
    """
    profile_str = json.dumps(
        {k: v for k, v in user_profile.items() if not k.startswith("_")},
        indent=2
    )
    patterns_str = json.dumps(stored_patterns[-10:], indent=2) if stored_patterns else "None"
    insights_str = json.dumps(accept_insights[-5:], indent=2) if accept_insights else "None"

    prompt = f"""TOPIC: {topic}

USER PROFILE:
{profile_str}

USER'S STORED LEARNING PATTERNS:
{patterns_str}

USER'S ACCEPTED INSIGHTS:
{insights_str}

CONTEXT INSTRUCTION GENERATED BY ContextManager Agent:
\"\"\"{context_instruction}\"\"\"

TASK: Rate this context instruction on SPECIFICITY — how well it synthesizes the user's
stored patterns and insights into actionable generation guidance, rather than just
restating the user's profile fields.

SPECIFICITY RUBRIC (1–5):
  5: Fully synthesizes stored patterns — references specific documented traits and turns
     them into a concrete, example-specific directive (e.g., "Use medical equipment
     analogies; ground quantities in clinical measurements").
  4: References specific stored patterns with a concrete directive.
  3: References stored patterns but directive is general (e.g., "use domain examples").
  2: Mentions stored domain preference but gives no actionable instruction.
  1: Restates profile fields only (name, role, location) — no reference to stored patterns.

Write 1-2 sentences of reasoning, then output:
SPECIFICITY_SCORE: [1-5]
"""
    try:
        response = _call_judge(prompt, model=model, api_key=api_key)
        score_match = re.search(r"SPECIFICITY_SCORE:\s*([1-5])", response)
        score = int(score_match.group(1)) if score_match else None
        return {
            "specificity_score": score,
            "reasoning": response,
            "error": None if score is not None else "Score not parsed",
        }
    except Exception as e:
        return {"specificity_score": None, "reasoning": "", "error": str(e)}


def batch_judge(
    examples: List[Dict[str, Any]],
    model: str = "gpt-4o",
    api_key: str = None,
    delay_seconds: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Batch judge a list of examples.
    Each item: {"example_text": str, "user_profile": dict, "topic": str, **extra_fields}
    Returns list with added "judgment" key.
    """
    results = []
    for i, item in enumerate(examples):
        print(f"  Judging {i+1}/{len(examples)}: {item.get('topic')} | {item.get('user_id', '')}")
        judgment = judge_example(
            example_text=item["example_text"],
            user_profile=item["user_profile"],
            topic=item["topic"],
            model=model,
            api_key=api_key,
        )
        result = {**item, "judgment": judgment}
        results.append(result)
        time.sleep(delay_seconds)
    return results
