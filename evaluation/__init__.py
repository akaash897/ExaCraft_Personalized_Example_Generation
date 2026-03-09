"""
ExaCraft Evaluation Framework
LLM-as-Judge test bench for evaluating personalized educational example quality.

Design basis:
  - G-Eval (Liu et al., 2023): Chain-of-thought before scoring for calibration
  - LLM-as-Judge (Zheng et al., 2023): Multi-judge ensemble for reliability
  - Krippendorff's alpha for inter-rater agreement measurement
  - Bloom's Revised Taxonomy for pedagogical quality rubrics
"""
