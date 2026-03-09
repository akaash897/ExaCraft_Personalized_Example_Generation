"""
Ollama-based LLM Judge

Uses locally-running Ollama models as evaluation judges.

Model family selection rationale (Zheng et al. 2023 — self-enhancement bias mitigation):
  ExaCraft generates examples with Gemini (Google). To minimize self-enhancement
  bias — where a judge from the same model family systematically prefers outputs
  from that family — all three judge models are from different, non-Google families:

  1. llama3.2:3b  — Meta LLaMA family. Compact, strong instruction following.
  2. mistral:7b   — Mistral AI family. Strong reasoning, well-calibrated.
  3. phi3:mini    — Microsoft Phi family. Efficient, good structured output.

  These three families provide diversity of training objectives, data, and RLHF
  approaches, reducing correlated errors in the ensemble (Wang et al., 2023).

  Fallback: gemma2:2b (Google, but different architecture/fine-tuning than Gemini Pro)

Temperature rationale:
  JUDGE_TEMPERATURE = 0.3: Low enough for consistency, high enough to allow
  multiple samples to diverge slightly for averaging (G-Eval protocol).
  Temperature = 0 causes identical outputs across samples — defeating multi-sample
  averaging. Temperature > 0.5 introduces too much noise.
"""

from __future__ import annotations

import json
import time
from typing import List, Optional

import requests

from evaluation.judges.base_judge import BaseJudge


# Default ollama endpoint
OLLAMA_BASE_URL = "http://localhost:11434"


class OllamaJudge(BaseJudge):
    """
    LLM judge backed by a locally-running Ollama model.

    Each call uses the /api/generate endpoint with stream=False.
    Retries up to MAX_RETRIES on connection errors.
    """

    MAX_RETRIES = 2
    RETRY_DELAY = 2  # seconds

    def __init__(
        self,
        model: str,
        name: Optional[str] = None,
        base_url: str = OLLAMA_BASE_URL,
        n_samples: int = 5,
        timeout: int = 120,
    ):
        """
        Args:
            model: Ollama model tag, e.g. "llama3.2:3b", "mistral:7b"
            name: Human-readable judge name (defaults to model tag)
            base_url: Ollama API base URL
            n_samples: Number of samples per dimension (G-Eval averaging)
            timeout: HTTP request timeout in seconds
        """
        super().__init__(name=name or model, model=model)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.N_SAMPLES = n_samples

    def _call_model(self, prompt: str, temperature: float, n_samples: int) -> List[str]:
        """
        Call Ollama model N times and return raw text responses.

        Ollama does not support batch sampling in a single request,
        so we make N sequential calls. This is intentional: independent
        calls eliminate any auto-regressive conditioning between samples.
        """
        responses = []
        for _ in range(n_samples):
            text = self._single_call(prompt, temperature)
            if text is not None:
                responses.append(text)
        return responses

    def _single_call(self, prompt: str, temperature: float) -> Optional[str]:
        """Single API call to Ollama with retry logic."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 512,   # cap tokens for structured JSON output
            },
            "format": "json",  # Ollama JSON mode — enforces valid JSON output
        }

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
            except requests.exceptions.ConnectionError:
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY)
                else:
                    print(f"  [OllamaJudge:{self.model}] Connection failed after {self.MAX_RETRIES + 1} attempts.")
                    return None
            except requests.exceptions.Timeout:
                print(f"  [OllamaJudge:{self.model}] Request timed out.")
                return None
            except Exception as e:
                print(f"  [OllamaJudge:{self.model}] Unexpected error: {e}")
                return None

    @staticmethod
    def check_ollama_available(base_url: str = OLLAMA_BASE_URL) -> bool:
        """Check if Ollama server is running."""
        try:
            r = requests.get(f"{base_url}/api/tags", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    @staticmethod
    def list_available_models(base_url: str = OLLAMA_BASE_URL) -> List[str]:
        """Return list of locally available model tags."""
        try:
            r = requests.get(f"{base_url}/api/tags", timeout=5)
            r.raise_for_status()
            data = r.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    @staticmethod
    def pull_model(model: str, base_url: str = OLLAMA_BASE_URL) -> bool:
        """Pull a model if not already available."""
        try:
            r = requests.post(
                f"{base_url}/api/pull",
                json={"name": model, "stream": False},
                timeout=600,
            )
            return r.status_code == 200
        except Exception:
            return False


# ──────────────────────────────────────────────────────────────────────────────
# Factory helper
# ──────────────────────────────────────────────────────────────────────────────

# Default judge panel — three families, all different from Gemini (the generator)
DEFAULT_JUDGE_MODELS = [
    ("llama3.2:3b",  "LlamaJudge"),    # Meta LLaMA family
    ("mistral:7b",   "MistralJudge"),  # Mistral AI family
    ("phi3:mini",    "PhiJudge"),      # Microsoft Phi family
]

# Lightweight fallback panel when RAM is constrained
LIGHTWEIGHT_JUDGE_MODELS = [
    ("llama3.2:1b",  "LlamaJudge"),
    ("phi3:mini",    "PhiJudge"),
    ("gemma2:2b",    "GemmaJudge"),
]


def build_judge_panel(
    models: List[tuple] = None,
    base_url: str = OLLAMA_BASE_URL,
    n_samples: int = 5,
) -> List[OllamaJudge]:
    """
    Build a list of OllamaJudge instances for the ensemble.

    Automatically falls back to whatever models are locally available
    if the default panel is not fully installed.

    Args:
        models: List of (model_tag, judge_name) tuples. Defaults to DEFAULT_JUDGE_MODELS.
        base_url: Ollama server URL.
        n_samples: Samples per dimension per judge.

    Returns:
        List of configured OllamaJudge instances.
    """
    if models is None:
        models = DEFAULT_JUDGE_MODELS

    available = set(OllamaJudge.list_available_models(base_url))
    judges = []

    for model_tag, judge_name in models:
        # Check exact match or prefix match (e.g. "llama3.2:3b" in "llama3.2:3b-instruct-q4_0")
        matched = next(
            (a for a in available if a == model_tag or a.startswith(model_tag.split(":")[0])),
            None
        )
        if matched:
            judges.append(OllamaJudge(
                model=matched,
                name=judge_name,
                base_url=base_url,
                n_samples=n_samples,
            ))
            print(f"  [JudgePanel] Loaded judge: {judge_name} -> {matched}")
        else:
            print(f"  [JudgePanel] WARNING: {model_tag} not found locally. "
                  f"Run: ollama pull {model_tag}")

    return judges
