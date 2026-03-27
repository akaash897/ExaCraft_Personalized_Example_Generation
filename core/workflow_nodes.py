"""
Workflow Node Implementations
Primary Agent nodes for Adaptive Example Generation (6 nodes).

node_load_profile          → load user profile from storage
node_build_context         → synthesize learning patterns + insights into context_instruction
node_generate              → call LLM with profile + context + optional regeneration_instruction
node_format_and_save       → save example to history, set example_id
node_user_review           → ⏸ interrupt for natural-language user feedback
node_process_feedback      → invoke Adaptive Response Agent, set regeneration flags
"""

import uuid
from datetime import datetime
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import interrupt

from core.user_profile import UserProfile
from core.learning_context import LearningContext
from core.workflow_state import PersonalizedGenerationState
from core.adaptive_response_agent import invoke_adaptive_response_agent
from core.example_history import ExampleHistory
from core.feedback_store import load_learning_patterns, load_accept_insights
from core.context_manager_agent import resolve_topic_tags, invoke_context_manager_agent
from core.llm_provider import LLMProviderFactory
from config.settings import DEFAULT_LLM_PROVIDER, LLM_API_KEYS


def _get_provider_and_key(state: PersonalizedGenerationState):
    provider = state.get("provider") or DEFAULT_LLM_PROVIDER
    api_key = LLM_API_KEYS.get(provider, "")
    return provider, api_key


# ─── Node 1: Load Profile ─────────────────────────────────────────────────────

def node_load_profile(state: PersonalizedGenerationState) -> PersonalizedGenerationState:
    """Load user profile via UserProfile class.

    eval_mode gate: t0 skips profile — generates with no personalization.
    """
    if state.get("eval_mode") == "t0":
        state["user_profile"] = {}
        state["profile_summary"] = "No profile available."
        state["error_occurred"] = False
        return state

    user_id = state["user_id"]
    try:
        profile = UserProfile(user_id=user_id)
        state["user_profile"] = profile.profile_data
        state["profile_summary"] = profile.get_profile_summary()
        state["error_occurred"] = False
    except Exception as e:
        state["user_profile"] = {}
        state["profile_summary"] = "Profile unavailable."
        state["error_occurred"] = True
        state["error_message"] = f"node_load_profile error: {e}"
    return state


# ─── Node 2: Build Context ────────────────────────────────────────────────────

def node_build_context(state: PersonalizedGenerationState) -> PersonalizedGenerationState:
    """
    Build a targeted context_instruction using the ContextManager Agent.

    1. Resolve 1-3 canonical topic tags for the current topic (LLM call).
    2. Cold start guard: if no patterns and no insights exist, skip agent.
    3. Invoke ContextManager Agent — it queries example history by tag,
       retrieves linked feedback, reasons over global signals as fallback,
       and emits a 2-3 sentence actionable instruction.

    eval_mode gate: skipped entirely for t0 and t1 (no context manager).
    """
    eval_mode = state.get("eval_mode")
    if eval_mode in ("t0", "t1"):
        state["context_instruction"] = ""
        return state

    user_id = state["user_id"]
    topic = state["topic"]
    provider, api_key = _get_provider_and_key(state)

    try:
        # Step 1: Resolve topic tags
        topic_tags = resolve_topic_tags(topic, provider, api_key)
        state["topic_tags"] = topic_tags

        # Step 2: Cold start guard
        patterns_data = load_learning_patterns(user_id)
        insights_data = load_accept_insights(user_id)
        if not patterns_data.get("patterns") and not insights_data.get("insights"):
            state["context_instruction"] = ""
            return state

        # Step 3: Invoke ContextManager Agent
        context_instruction = invoke_context_manager_agent(
            user_id=user_id,
            topic=topic,
            topic_tags=topic_tags,
            provider=provider,
            api_key=api_key
        )
        state["context_instruction"] = context_instruction

    except Exception as e:
        state["context_instruction"] = ""
        state["error_message"] = f"node_build_context warning: {e}"

    return state


# ─── Node 3: Generate ─────────────────────────────────────────────────────────

def node_generate(state: PersonalizedGenerationState) -> PersonalizedGenerationState:
    """
    Generate a personalized example using the LLM.

    Reads from state:
        profile_summary          — who the user is
        context_instruction      — synthesized from learning history (node_build_context)
        regeneration_instruction — specific fix requested by Adaptive Response Agent (if looping)

    Clears regeneration_instruction after use so it doesn't leak into further loops.
    """
    user_id = state["user_id"]
    topic = state["topic"]
    profile_summary = state.get("profile_summary", "No profile available.")
    context_instruction = state.get("context_instruction", "")
    regeneration_instruction = state.get("regeneration_instruction", "")
    provider, api_key = _get_provider_and_key(state)

    try:
        if not api_key:
            raise ValueError(f"API key not configured for provider: {provider}")

        # Build learning context base — gated for T0 to prevent cross-tier contamination
        eval_mode = state.get("eval_mode")
        if eval_mode == "t0":
            base_context = "No prior learning history."
            learning_context = None
        else:
            learning_context = LearningContext(user_id=user_id)
            base_context = learning_context.get_learning_state_summary()

        # Compose enriched context (personalization only — no regen here)
        enriched_context = base_context
        if context_instruction:
            enriched_context += f"\n\nPERSONALIZATION INSTRUCTION (from learning history):\n{context_instruction}"

        # Clear regeneration instruction after consuming it
        state["regeneration_instruction"] = ""

        llm = LLMProviderFactory.create_llm(provider, api_key, temperature=0.3)

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an adaptive AI tutor that generates structured, personalized examples.\n\n"

             # ── WHAT TO GENERATE ─────────────────────────────────────────────
             "WHAT TO GENERATE (non-negotiable):\n"
             "  - An example that EXPLAINS the topic to the student. The topic is the concept to teach.\n"
             "  - Do NOT reframe the topic as a project to build or a task to automate.\n"
             "    e.g. topic='Fishing' → explain what fishing is, not how to code a fishing log.\n"
             "    e.g. topic='Supply and Demand' → explain the concept, not how to model it in Python.\n"
             "  - Topic accuracy comes first — never sacrifice it.\n\n"

             # ── COMPLEXITY RULES (fix: removed arbitrary line cap; defined 'mixed') ──
             "COMPLEXITY RULES — match the student's stated level exactly:\n"
             "  simple   → 1 scenario, plain English, no jargon, no formulas unless trivial.\n"
             "             Prioritise analogy and concrete imagery over technical terms.\n"
             "             Length should be as short as the topic allows — stop when the concept is clear.\n"
             "  medium   → 1 scenario, one numeric example or formula if relevant, moderate depth.\n"
             "             Introduce key terms but define them inline.\n"
             "  advanced → Full depth: formulas, edge cases, trade-offs, complexity analysis where relevant.\n"
             "             Assume the student can handle technical notation.\n"
             "  mixed    → Start at medium depth, then add one advanced extension at the end.\n"
             "             Label the extension clearly (e.g. 'Going deeper:').\n\n"

             # ── PERSONALIZATION (fix: conditional on profile availability) ───
             "HOW TO PERSONALIZE:\n"
             "  - If a profile is provided: use the student's name, location, and profession to ground\n"
             "    the scenario in their world. Make the example feel written specifically for them.\n"
             "  - If no profile is available: generate a clear, generic example with no assumed\n"
             "    demographics, names, or locations. Do NOT invent a persona.\n"
             "  - Apply the context instruction only if it is relevant to the topic domain.\n"
             "    e.g. 'use Python code' is relevant for programming topics, NOT for biology or history.\n"
             "  - If the context instruction conflicts with the topic domain, ignore it and use the profile.\n\n"

             # ── OUTPUT FORMAT ─────────────────────────────────────────────────
             "OUTPUT FORMAT:\n"
             "  Use a structured format suited to the topic domain — do not force fixed field labels.\n"
             "  Always begin with 'Concept:' and 'Example:', then add fields appropriate for the topic.\n"
             "  End every example with a 'Key Insight:' section (1–2 sentences, the takeaway).\n\n"

             # ── WHAT NOT TO DO (negative examples) ───────────────────────────
             "WHAT NOT TO DO — these are grading failures:\n"
             "  [BAD — complexity mismatch] Profile says simple, but output uses formulas and jargon:\n"
             "    ✗ 'Using the logistic function σ(z) = 1/(1+e^{{-z}}), the model computes...'\n"
             "    ✓ 'The model looks at hundreds of past examples and learns which patterns lead to which outcomes.'\n\n"
             "  [BAD — domain bleed] CS context leaks into a non-CS topic:\n"
             "    ✗ (for Photosynthesis) 'We can model this in Python: chlorophyll.absorb(sunlight)'\n"
             "    ✓ Photosynthesis uses biological process framing — no code.\n\n"
             "  [BAD — invented persona when no profile exists] No profile provided, but output invents one:\n"
             "    ✗ 'Priya, a software engineer in Bangalore, applies this to her work...'\n"
             "    ✓ 'Consider a factory that produces widgets...' (generic, no assumed identity)\n\n"

             # ── GOOD OUTPUT EXAMPLES ──────────────────────────────────────────
             "EXAMPLES OF GOOD OUTPUT:\n\n"

             "--- [STEM — formula topic, advanced, profession-grounded]\n"
             "Profile: Nurse | professional | advanced complexity\n"
             "Context: Medical domain analogies work well.\n"
             "Topic: Newton's Second Law\n\n"
             "Concept: Newton's Second Law (F = ma)\n\n"
             "Example:\n"
             "A nurse pushes a patient gurney down a hospital corridor.\n"
             "A heavier patient requires more force to reach the same speed.\n\n"
             "Given:\n"
             "  - Force applied: 100 N\n"
             "  - Gurney + patient mass: 50 kg\n\n"
             "Formula:\n"
             "  F = m × a\n"
             "  a = F / m = 100 / 50 = 2 m/s²\n\n"
             "Result:\n"
             "  The gurney accelerates at 2 m/s²\n\n"
             "Key Insight:\n"
             "  Double the mass → half the acceleration for the same push.\n"
             "  This is why moving a heavier patient requires significantly\n"
             "  more effort than pushing an empty gurney.\n\n"

             "--- [STEM — process topic, simple, personalized]\n"
             "Profile: Student | high_school | simple complexity\n"
             "Context: Student is a visual learner who likes step-by-step breakdowns.\n"
             "Topic: Photosynthesis\n\n"
             "Concept: Photosynthesis\n\n"
             "Example:\n"
             "Think of a plant as a tiny solar-powered kitchen.\n"
             "Every morning it collects three ingredients and cooks its own food.\n\n"
             "Ingredients:\n"
             "  - Sunlight → the energy source (like electricity for the oven)\n"
             "  - CO₂ from air → one raw ingredient\n"
             "  - Water from soil → the other raw ingredient\n\n"
             "What it makes:\n"
             "  - Glucose → food the plant uses to grow\n"
             "  - Oxygen → released as a by-product (what we breathe)\n\n"
             "Where it happens:\n"
             "  Inside tiny green structures in the leaf called chloroplasts.\n\n"
             "Key Insight:\n"
             "  No sunlight → no cooking → no food → plant starves.\n"
             "  That is why plants grow toward light.\n\n"

             "--- [Social Science — comparative/causal topic, medium, profession-grounded]\n"
             "Profile: Business Analyst | postgraduate | medium complexity\n"
             "Context: User works with market data; real-world pricing examples resonate.\n"
             "Topic: Supply and Demand\n\n"
             "Concept: Supply and Demand\n\n"
             "Example:\n"
             "A business analyst tracks ticket prices for a music festival.\n"
             "When the headliner is announced, demand jumps but seat count stays fixed.\n\n"
             "What changes:\n"
             "  - Demand increases  → more buyers competing for the same supply\n"
             "  - Supply is fixed   → venue capacity does not change\n"
             "  - Result            → price rises until fewer buyers can afford it\n\n"
             "If the headliner cancels:\n"
             "  - Demand drops sharply\n"
             "  - Supply unchanged → price falls to attract remaining buyers\n\n"
             "Key Insight:\n"
             "  Price is the signal that balances how much people want something\n"
             "  against how much of it exists. Shift either side and the price moves.\n\n"

             "--- [Abstract / conceptual topic, medium, no profile provided]\n"
             "Profile: No profile available.\n"
             "Context: No prior signals.\n"
             "Topic: Entropy\n\n"
             "Concept: Entropy\n\n"
             "Example:\n"
             "Consider a shuffled deck of cards.\n"
             "There is exactly one arrangement that counts as 'perfectly sorted'\n"
             "but millions of arrangements that count as 'shuffled'.\n\n"
             "Why disorder dominates:\n"
             "  - A random cut is almost certain to land in a disordered state\n"
             "    simply because there are overwhelmingly more disordered states.\n"
             "  - Restoring order requires deliberate effort — it does not happen by chance.\n\n"
             "Entropy in one sentence:\n"
             "  Entropy measures how many equivalent arrangements a system can be in —\n"
             "  high entropy means many possibilities (disorder is the default),\n"
             "  low entropy means very few (order must be actively maintained).\n\n"
             "Key Insight:\n"
             "  Entropy does not prefer chaos. It just reflects that chaos has\n"
             "  overwhelmingly more ways to exist than order does.\n\n"

             "--- [CS — applied topic, advanced, context instruction applied]\n"
             "Profile: Software Engineer | undergraduate | advanced complexity\n"
             "Context: User prefers code-level intuition with complexity trade-offs.\n"
             "Topic: Recursion\n\n"
             "Concept: Recursion\n\n"
             "Example:\n"
             "A software engineer implements a function to compute the factorial of n.\n"
             "Instead of a loop, the function calls itself with a smaller input each time.\n\n"
             "Code sketch:\n"
             "  def factorial(n):\n"
             "      if n == 0: return 1        # base case — stops the recursion\n"
             "      return n * factorial(n-1)  # recursive case\n\n"
             "Call stack for factorial(4):\n"
             "  factorial(4) → 4 × factorial(3)\n"
             "               → 4 × 3 × factorial(2)\n"
             "               → 4 × 3 × 2 × factorial(1)\n"
             "               → 4 × 3 × 2 × 1 × factorial(0) = 1\n"
             "  Unwinds to: 4 × 3 × 2 × 1 × 1 = 24\n\n"
             "Trade-offs:\n"
             "  - Time:  O(n) — one call per decrement\n"
             "  - Space: O(n) — each call occupies a stack frame until base case hits\n"
             "  - Risk:  stack overflow for very large n without tail-call optimisation\n\n"
             "Key Insight:\n"
             "  Recursion works by reducing a problem to a smaller version of itself.\n"
             "  Every recursive solution needs a base case — without one it recurses forever.\n\n"

             # ── REGENERATION EXAMPLE (fix: teaches the model the before/after pattern) ──
             "--- [REGENERATION — how to revise an existing example based on feedback]\n"
             "Original example was: a medium-complexity Supply and Demand example using festival tickets.\n"
             "Student feedback: 'This is too complicated. Can you use something simpler?'\n"
             "Regeneration instruction: Simplify to simple complexity; use a single everyday object.\n\n"
             "Concept: Supply and Demand\n\n"
             "Example:\n"
             "Think about umbrellas on a rainy day.\n"
             "Everyone wants one, but the shop only has a few left.\n\n"
             "What happens:\n"
             "  - Many buyers, few umbrellas → the shop can charge more\n"
             "  - If it stops raining, fewer people want one → price drops\n\n"
             "Key Insight:\n"
             "  When more people want something than there is available,\n"
             "  the price goes up. When fewer people want it, the price comes down.\n\n"
             "---\n\n"

             # ── RUNTIME SLOTS ─────────────────────────────────────────────────
             "STUDENT PROFILE:\n{user_profile}\n\n"
             "{learning_context_block}"
             "{regeneration_override}"
             "Now generate a structured example for the topic below.\n"
             "Match the complexity level stated in the profile exactly.\n"
             "Adapt field labels to suit the topic — do not copy example fields blindly.\n"
             "Output ONLY the structured example. No meta-commentary."),
            ("human", "Generate an example for the topic: {topic}")
        ])

        # Build learning context block — only shown when there is something meaningful to say
        if enriched_context and enriched_context not in ("No prior learning history.", "First time learning session"):
            learning_context_block = f"LEARNING CONTEXT:\n{enriched_context}\n\n"
        else:
            learning_context_block = ""

        # Regeneration instruction overrides profile complexity — student feedback takes priority
        if regeneration_instruction:
            regeneration_override = (
                "STUDENT FEEDBACK OVERRIDE (highest priority — supersedes profile complexity):\n"
                f"{regeneration_instruction}\n"
                "Apply this change exactly. Refer to the regeneration example above for the expected pattern.\n\n"
            )
        else:
            regeneration_override = ""

        chain = prompt | llm
        result = chain.invoke({
            "user_profile": profile_summary,
            "learning_context_block": learning_context_block,
            "regeneration_override": regeneration_override,
            "topic": topic
        })

        # DeepSeek (and some OpenRouter models) return content as a list of blocks
        raw_content = result.content
        if isinstance(raw_content, list):
            raw_content = "".join(
                b.get("text", "") if isinstance(b, dict) else str(b)
                for b in raw_content
            )
        example_text = raw_content.strip()

        if example_text.startswith("Error generating example:"):
            state["error_occurred"] = True
            state["error_message"] = example_text
            state["generated_example"] = None
        else:
            state["generated_example"] = example_text
            state["example_metadata"] = {
                "topic": topic,
                "provider": provider,
                "had_context_instruction": bool(context_instruction),
                "was_regeneration": bool(regeneration_instruction),
                "generation_timestamp": datetime.now().isoformat()
            }
            state["error_occurred"] = False

        # Record topic interaction in learning context (skip for T0 — prevents within-tier leak)
        if learning_context is not None:
            learning_context.add_topic_interaction(topic)

    except Exception as e:
        state["error_occurred"] = True
        state["error_message"] = f"node_generate error: {e}"
        state["generated_example"] = None

    return state


# ─── Node 4: Format and Save ──────────────────────────────────────────────────

def node_format_and_save(state: PersonalizedGenerationState) -> PersonalizedGenerationState:
    """
    Save example to ExampleHistory and populate display fields.

    eval_mode gate:
      t0 — skip disk write entirely. T0 has no profile so its examples would
            corrupt the example_history that T2/T3 ContextManager reads.
      t1 — skip disk write. T1 has a profile but no context manager, so its
            examples were generated without context signals and should not be
            treated as meaningful history for T2/T3.
      t2, t3, None — save as normal.
    """
    user_id = state["user_id"]
    topic = state["topic"]
    generated_example = state.get("generated_example", "")
    example_metadata = state.get("example_metadata", {})
    profile_data = state.get("user_profile", {})
    eval_mode = state.get("eval_mode")

    # Generate a stable example_id regardless of whether we save to disk
    example_id = f"ex_{uuid.uuid4().hex[:16]}"

    try:
        # Resolve tags (needed for save and for display_metadata)
        tags = state.get("topic_tags")
        if not tags:
            try:
                provider_fs, api_key_fs = _get_provider_and_key(state)
                tags = resolve_topic_tags(topic, provider_fs, api_key_fs)
                state["topic_tags"] = tags
            except Exception:
                tags = ["general_concept"]

        # Only write to disk for t2, t3, and production (None) — not for t0/t1
        if eval_mode not in ("t0", "t1"):
            history = ExampleHistory(user_id=user_id)
            example_id = history.record_example(
                topic=topic,
                example_text=generated_example,
                profile_snapshot=profile_data,
                learning_context_snapshot=example_metadata,
                similar_users=[],
                tags=tags
            )

        state["example_id"] = example_id
        state["example_record"] = {
            "example_id": example_id,
            "topic": topic,
            "example_text": generated_example,
            "metadata": example_metadata,
            "timestamp": datetime.now().isoformat()
        }
        state["formatted_example"] = {
            "example_id": example_id,
            "topic": topic,
            "text": generated_example
        }
        state["display_metadata"] = {
            "topic": topic,
            "example_id": example_id,
            "generated_at": datetime.now().isoformat(),
            "provider": example_metadata.get("provider", "unknown"),
            "loop_count": state.get("loop_count", 0)
        }

    except Exception as e:
        fallback_id = f"ex_{uuid.uuid4().hex[:12]}"
        state["example_id"] = fallback_id
        state["formatted_example"] = {
            "example_id": fallback_id,
            "topic": topic,
            "text": generated_example
        }
        state["display_metadata"] = {
            "topic": topic,
            "example_id": fallback_id,
            "generated_at": datetime.now().isoformat()
        }
        state["error_message"] = f"node_format_and_save warning: {e}"

    return state


# ─── Node 5: User Review (Interrupt) ─────────────────────────────────────────

def node_user_review(state: PersonalizedGenerationState) -> PersonalizedGenerationState:
    """
    Interrupt workflow to collect natural-language user feedback.
    LangGraph pauses here and returns thread_id + example to the caller.
    Resumes when POST /workflows/{thread_id}/resume is called with user_feedback_text.
    """
    feedback = interrupt({
        "example": state.get("formatted_example"),
        "metadata": state.get("display_metadata"),
        "prompt": "What did you think of this example?"
    })

    return {
        "user_feedback_text": feedback.get("user_feedback_text", ""),
    }


# ─── Node 6: Process Feedback ─────────────────────────────────────────────────

def node_process_feedback(state: PersonalizedGenerationState) -> PersonalizedGenerationState:
    """
    Invoke the Adaptive Response Agent with the user's natural-language feedback.
    The agent autonomously decides to call regenerate / accept / flag_pattern.
    Writes regeneration_requested + regeneration_instruction back into state.

    eval_mode gate: skipped for t0/t1/t2 — no feedback loop processing.
    """
    eval_mode = state.get("eval_mode")
    if eval_mode in ("t0", "t1", "t2"):
        state["regeneration_requested"] = False
        state["regeneration_instruction"] = ""
        state["feedback_processed"] = False
        state["last_agent_action"] = "skipped"
        state["workflow_completed_at"] = datetime.now().isoformat()
        return state

    user_id = state["user_id"]
    example_id = state.get("example_id", "")
    topic = state["topic"]
    generated_example = state.get("generated_example") or ""
    user_feedback_text = state.get("user_feedback_text") or ""
    provider, api_key = _get_provider_and_key(state)

    # If generation failed upstream, skip feedback processing
    if state.get("error_occurred") and not generated_example:
        state["regeneration_requested"] = False
        state["regeneration_instruction"] = ""
        state["feedback_processed"] = False
        state["last_agent_action"] = "skipped"
        state["workflow_completed_at"] = datetime.now().isoformat()
        return state

    try:
        patterns = load_learning_patterns(user_id)

        result = invoke_adaptive_response_agent(
            user_id=user_id,
            example_id=example_id,
            topic=topic,
            example_text=generated_example,
            user_feedback_text=user_feedback_text,
            user_profile=state.get("user_profile", {}),
            pattern_history=patterns,
            provider=provider,
            api_key=api_key
        )

        state["regeneration_requested"] = result.get("regeneration_requested", False)
        state["regeneration_instruction"] = result.get("regeneration_instruction", "")
        state["feedback_processed"] = result.get("feedback_recorded", False)
        state["loop_count"] = state.get("loop_count", 0) + 1
        state["workflow_completed_at"] = datetime.now().isoformat()

        # Derive last_agent_action from agent decisions
        agent_decisions = result.get("agent_decisions", [])
        if state["regeneration_requested"]:
            state["last_agent_action"] = "regenerate"
        elif any(d.get("tool") == "flag_pattern" for d in agent_decisions):
            state["last_agent_action"] = "flag_pattern"
        else:
            state["last_agent_action"] = "accept"

    except Exception as e:
        state["regeneration_requested"] = False
        state["regeneration_instruction"] = ""
        state["feedback_processed"] = False
        state["error_occurred"] = True
        state["error_message"] = f"node_process_feedback error: {e}"
        state["workflow_completed_at"] = datetime.now().isoformat()

    return state
