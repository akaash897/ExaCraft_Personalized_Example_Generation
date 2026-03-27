# ExaCraft Evaluation Results

**Design:** 8 synthetic users (4 profiles x 2 start modes) x 4 topics = 32 cells per tier.
**Tiers:** T0 (generic), T1 (+profile), T2 (+context instruction), T3 (full feedback loop).
**Composite:** 0.20 PF + 0.20 CC + 0.30 CA + 0.20 PC + 0.10 DA (scale 1-5).
**Primary judge:** GPT-4.1-nano | **Secondary judge:** Llama 3.3 70B (20% subsample).

---

## 1. Ablation (Composite Scores by Tier)

| Tier | DeepSeek V3.2 | GPT-5-nano | Description |
|------|:---:|:---:|---|
| T0 | 4.257 | 3.712 | Generic (no profile, no context) |
| T1 | 4.809 | 4.388 | + User profile |
| T2 | 4.859 | 4.791 | + Context instruction |
| T3 | 4.888 | 4.981 | + Feedback loop (full system) |
| **T0 -> T1** | **+0.552** | **+0.676** | |
| **T0 -> T3** | **+0.631** | **+1.269** | |

### Per-Axis Breakdown — DeepSeek V3.2

| Axis | T0 | T1 | T2 | T3 |
|------|:---:|:---:|:---:|:---:|
| PF (Personalization Fidelity) | 2.73 | 4.80 | 4.93 | 4.99 |
| CC (Complexity Calibration) | 4.13 | 4.35 | 4.43 | 4.47 |
| CA (Conceptual Accuracy) | 4.94 | 4.99 | 5.00 | 5.00 |
| PC (Pedagogical Clarity) | 4.82 | 4.93 | 4.95 | 4.99 |
| DA (Domain Appropriateness) | 4.39 | 4.95 | 4.99 | 5.00 |

### Per-Axis Breakdown — GPT-5-nano

| Axis | T0 | T1 | T2 | T3 |
|------|:---:|:---:|:---:|:---:|
| PF (Personalization Fidelity) | 2.09 | 3.47 | 4.34 | 4.94 |
| CC (Complexity Calibration) | 3.78 | 4.38 | 4.84 | 5.00 |
| CA (Conceptual Accuracy) | 4.41 | 4.78 | 4.97 | 5.00 |
| PC (Pedagogical Clarity) | 4.00 | 4.53 | 4.88 | 4.97 |
| DA (Domain Appropriateness) | 4.16 | 4.78 | 4.88 | 5.00 |

---

## 2. Feedback Compliance Rate (FCR) — T3 Only

FCR measures whether regenerated examples address the user's feedback (compliance score >= threshold).

| Metric | DeepSeek V3.2 | GPT-5-nano |
|--------|:---:|:---:|
| **Overall n** | 41 | 55 |
| **FCR@3** | 1.000 | 0.945 |
| **FCR@4** | 0.902 | 0.891 |
| **Mean score** | 4.341 | 4.564 |

### By Feedback Type

| | DeepSeek easy | DeepSeek adv. | GPT-5-nano easy | GPT-5-nano adv. |
|---|:---:|:---:|:---:|:---:|
| n | 28 | 13 | 40 | 15 |
| FCR@3 | 1.000 | 1.000 | 0.925 | 1.000 |
| FCR@4 | 1.000 | 0.692 | 0.850 | 1.000 |
| Mean | 4.536 | 3.923 | 4.475 | 4.800 |

---

## 3. Loop Utilization Rate (LUR) — T3 Only

LUR measures the fraction of T3 sessions where the agent triggered at least one regeneration.

| Metric | DeepSeek V3.2 | GPT-5-nano |
|--------|:---:|:---:|
| **Overall** | 0.938 (30/32) | 0.969 (31/32) |
| Easy (cold) | 1.000 (16/16) | 1.000 (16/16) |
| Adversarial (warm) | 0.875 (14/16) | 0.938 (15/16) |

---

## 4. Pattern Persistence Utilization (PPU)

PPU measures whether stored learning patterns improve personalization at generation time.
Delta PF = mean PF(warm, T3) - mean PF(warm, T1).

| Metric | DeepSeek V3.2 | GPT-5-nano |
|--------|:---:|:---:|
| Warm T3 PF | 5.000 | 5.000 |
| Warm T1 PF | 4.688 | 3.062 |
| Cold T3 PF | 4.979 | 4.875 |
| **Delta PF** | **+0.312** | **+1.938** |
| n (warm T3 / warm T1 / cold T3) | 16 / 16 / 16 | 16 / 16 / 16 |

---

## 5. Inter-Judge Agreement (Cohen's Kappa)

Secondary judge (Llama 3.3 70B) scored a 20% subsample of cells. Cohen's kappa is computed
over all five axes of each subsampled cell (integer scores 1-5).

| Metric | DeepSeek V3.2 | GPT-5-nano |
|--------|:---:|:---:|
| Subsampled cells | 26 | 26 |
| Axis-level pairs | 130 | 130 |
| Exact agreement | 107 (82.3%) | 107 (82.3%) |
| Off by 1 | 13 (10.0%) | 22 (16.9%) |
| Off by 2+ | 10 (7.7%) | 1 (0.8%) |
| **Cohen's kappa** | **0.607** | **0.681** |
| Interpretation | Substantial | Substantial |

---

## 6. Cross-Provider Summary

| Metric | DeepSeek V3.2 | GPT-5-nano | Notes |
|--------|:---:|:---:|---|
| T0 composite | 4.257 | 3.712 | DeepSeek stronger baseline |
| T3 composite | 4.888 | 4.981 | GPT-5-nano converges higher |
| T0->T3 gain | +0.631 | +1.269 | GPT-5-nano benefits more from full pipeline |
| FCR@4 | 0.902 | 0.891 | Comparable compliance |
| LUR | 0.938 | 0.969 | Both high loop utilization |
| PPU delta PF | +0.312 | +1.938 | GPT-5-nano shows larger pattern benefit |
| Cells (n per tier) | 32 | 32 | 8 users x 4 topics |
