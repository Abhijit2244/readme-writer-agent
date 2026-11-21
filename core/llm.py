"""
Gemini AI Enhancement Engine (Optional Cloud AI Mode)
=====================================================
Provides optional Large Language Model semantic enhancement via Google's Gemini 2.0 Flash API.

Features:
  • Zero-dependency implementation using Python's standard urllib.request.
  • Granular timeout guards (6-8s) preventing API hangs.
  • Graceful fallback to deterministic AST heuristics if API key is absent, offline, or rate-limited.
  • Enriches function/class commentaries for undocumented functions.
  • Generates tailored executive overviews and project architecture narratives.

All functions contain comprehensive educational commentary explaining hybrid LLM-AST architectures.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any


class GeminiEnhancer:
    """
    Optional semantic enrichment client powered by Google Gemini 2.0 Flash.
    """

    # Official Generative Language REST API endpoint for Gemini 2.0 Flash
    API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the Gemini enhancer.

        Args:
            api_key: Optional explicit API key. If omitted, checks os.environ['GEMINI_API_KEY'].
        """
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()

    def is_available(self) -> bool:
        """
        Returns True if a non-empty API key is configured.
        """
        return bool(self.api_key)

    def generate_text(self, prompt: str, timeout: int = 8) -> Optional[str]:
        """
        Submits a prompt to Gemini 2.0 Flash via standard HTTP POST.

        Operational Mechanics:
        1. Validates API key presence.
        2. Constructs the standard Gemini REST JSON payload.
        3. Sets low temperature (0.2) for deterministic, factual summaries.
        4. Enforces a strict network timeout to prevent hanging.
        5. Returns parsed candidate text, or None on any network/quota failure.

        Args:
            prompt: Text prompt instructions for Gemini.
            timeout: Maximum seconds to wait before falling back.

        Returns:
            Generated text string, or None if unavailable/failed.
        """
        if not self.is_available():
            return None

        url = f"{self.API_URL}?key={self.api_key}"
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 250
            }
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                candidates = result.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
        except Exception:
            # Graceful degradation: never crash on network failure or invalid key
            return None

        return None

    def enhance_commentary(self, entity_name: str, code_snippet: str, fallback_comment: str) -> str:
        """
        Enriches a function or class description using Gemini.

        Args:
            entity_name: Name of the function, method, or class.
            code_snippet: Short excerpt of the source code.
            fallback_comment: Pre-computed heuristic or docstring fallback.

        Returns:
            AI-enriched operational description, or fallback_comment if API is unavailable.
        """
        if not self.is_available():
            return fallback_comment

        prompt = (
            f"Describe what this code entity does in one concise, professional sentence (under 18 words). "
            f"Do not start with 'This function' or 'This class'. Output ONLY the single operational description sentence.\n\n"
            f"Entity: {entity_name}\nCode:\n{code_snippet[:500]}"
        )

        ai_response = self.generate_text(prompt, timeout=6)
        if ai_response:
            cleaned = ai_response.replace("\n", " ").strip("\"' ")
            if cleaned and len(cleaned) > 5:
                return cleaned

        return fallback_comment

    def enhance_executive_summary(self, repo_name: str, tech_stack: str, fallback_summary: str) -> str:
        """
        Generates an executive project overview pitch using Gemini.

        Args:
            repo_name: Name of the repository.
            tech_stack: Primary technologies and languages detected.
            fallback_summary: Default template overview string.

        Returns:
            AI-generated executive summary, or fallback_summary if unavailable.
        """
        if not self.is_available():
            return fallback_summary

        prompt = (
            f"Write a compelling 2-sentence executive summary and developer pitch for an open-source project named '{repo_name}'. "
            f"Tech Stack: {tech_stack}. Focus on reliability, clean architecture, and developer utility. Keep it under 45 words."
        )

        ai_response = self.generate_text(prompt, timeout=7)
        if ai_response:
            cleaned = ai_response.replace("\n\n", " ").replace("\n", " ").strip()
            if cleaned and len(cleaned) > 15:
                return cleaned

        return fallback_summary
