"""
Event validation using Perplexity API Sonar Reasoning.

Этот модуль использует Perplexity Sonar Reasoning API для проверки того,
являются ли события на разных платформах (Polymarket, SX, Kalshi) одинаковыми.
"""

import logging
import os
from typing import Any, Dict, Optional

import aiohttp
from aiohttp import ClientSession

from utils.retry import retry


class EventValidationError(Exception):
    """Raised when event validation fails."""


class EventValidator:
    """Validates events across different prediction markets using Perplexity API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the validator.

        Args:
            api_key: Perplexity API key. If not provided, will try to read from
                     PERPLEXITY_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            logging.warning(
                "PERPLEXITY_API_KEY not set. Event validation will be disabled."
            )
        self.api_url = "https://api.perplexity.ai/chat/completions"
        self.model = "sonar-reasoning"  # Chain-of-Thought reasoning model

    @retry()
    async def validate_events(
        self,
        session: ClientSession,
        event1_name: str,
        event1_description: str,
        platform1: str,
        event2_name: str,
        event2_description: str,
        platform2: str,
    ) -> Dict[str, Any]:
        """
        Validate if two events are the same using Perplexity Sonar Reasoning API.

        Args:
            session: aiohttp ClientSession
            event1_name: Name of the first event
            event1_description: Description of the first event
            platform1: Platform name (e.g., 'Polymarket')
            event2_name: Name of the second event
            event2_description: Description of the second event
            platform2: Platform name (e.g., 'Kalshi')

        Returns:
            Dictionary with validation results:
            {
                'are_same': bool,  # Whether events are the same
                'confidence': str,  # 'high', 'medium', 'low'
                'reasoning': str,  # Chain-of-thought explanation
                'warning': Optional[str]  # Warnings if any
            }

        Raises:
            EventValidationError: If API request fails or response is invalid
        """
        if not self.api_key:
            # CRITICAL SECURITY: Fail-safe approach - do not assume events are the same
            # if validation is disabled. This prevents dangerous arbitrage between
            # different events when PERPLEXITY_API_KEY is not configured.
            #
            # To explicitly allow unvalidated trading (NOT RECOMMENDED), set:
            # ALLOW_UNVALIDATED_EVENTS=true in .env
            allow_unvalidated = os.getenv("ALLOW_UNVALIDATED_EVENTS", "false").lower() == "true"

            if not allow_unvalidated:
                logging.error(
                    "Event validation BLOCKED: PERPLEXITY_API_KEY not set and "
                    "ALLOW_UNVALIDATED_EVENTS is not enabled. "
                    "This is a FAIL-SAFE to prevent arbitrage between different events."
                )
                raise EventValidationError(
                    "Event validation required but PERPLEXITY_API_KEY not configured. "
                    "Either set PERPLEXITY_API_KEY or explicitly enable ALLOW_UNVALIDATED_EVENTS=true "
                    "(NOT RECOMMENDED for production)"
                )

            # User explicitly allowed unvalidated events - proceed with warning
            logging.warning(
                "Event validation skipped: API key not set but ALLOW_UNVALIDATED_EVENTS=true. "
                "THIS IS DANGEROUS - you may trade between different events!"
            )
            return {
                "are_same": True,  # User accepted the risk
                "confidence": "unknown",
                "reasoning": "Validation disabled: API key not set, user allowed unvalidated",
                "warning": "Event validation is disabled - RISK OF TRADING DIFFERENT EVENTS",
            }

        # Build the prompt for reasoning
        prompt = self._build_validation_prompt(
            event1_name,
            event1_description,
            platform1,
            event2_name,
            event2_description,
            platform2,
        )

        try:
            timeout = aiohttp.ClientTimeout(total=30.0, connect=10.0)
            async with session.post(
                self.api_url,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "reasoning_effort": "high",  # Enable deep reasoning
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=timeout,
            ) as r:
                if r.status != 200:
                    error_text = await r.text()
                    logging.error(
                        "Perplexity API returned status %s: %s", r.status, error_text
                    )
                    raise EventValidationError(f"API returned status {r.status}")

                data = await r.json()

        except aiohttp.ClientError as exc:
            logging.error("Perplexity API request failed: %s", exc, exc_info=True)
            raise EventValidationError(f"API request failed: {exc}") from exc

        # Parse the response
        try:
            result = self._parse_response(data)
            logging.info(
                "Event validation: %s vs %s on %s vs %s -> %s (confidence: %s)",
                event1_name,
                event2_name,
                platform1,
                platform2,
                "SAME" if result["are_same"] else "DIFFERENT",
                result["confidence"],
            )
            return result
        except (KeyError, ValueError, TypeError) as exc:
            logging.error("Failed to parse Perplexity response: %s", exc, exc_info=True)
            raise EventValidationError(f"Invalid API response: {exc}") from exc

    def _build_validation_prompt(
        self,
        event1_name: str,
        event1_description: str,
        platform1: str,
        event2_name: str,
        event2_description: str,
        platform2: str,
    ) -> str:
        """Build a prompt for event validation."""
        return f"""You are an expert analyst comparing prediction market events across different platforms.  # noqa: E501

Task: Determine if the following two events refer to the SAME real-world occurrence.

**Event 1 ({platform1}):**
- Name: {event1_name}
- Description: {event1_description}

**Event 2 ({platform2}):**
- Name: {event2_name}
- Description: {event2_description}

**Instructions:**
1. Analyze both events carefully
2. Consider:
   - Do they reference the same real-world event?
   - Do they have the same resolution criteria?
   - Are the outcomes interpreted the same way?
   - Are there any subtle differences in wording that could lead to different outcomes?

3. Provide your answer in this EXACT format:
```
VERDICT: [SAME/DIFFERENT]
CONFIDENCE: [HIGH/MEDIUM/LOW]
REASONING: [Your detailed chain-of-thought analysis]
WARNING: [Any warnings about potential ambiguities, or NONE]
```

Be thorough in your analysis. Even small differences in resolution criteria can make events incompatible for arbitrage."""  # noqa: E501

    def _parse_response(self, data: Dict) -> Dict[str, Any]:
        """Parse Perplexity API response."""
        # Extract the content from the response
        content = data["choices"][0]["message"]["content"]

        # Parse the structured output
        lines = content.strip().split("\n")
        result = {
            "are_same": False,
            "confidence": "unknown",
            "reasoning": "",
            "warning": None,
        }

        for line in lines:
            line = line.strip()
            if line.startswith("VERDICT:"):
                verdict = line.split(":", 1)[1].strip().upper()
                result["are_same"] = verdict == "SAME"
            elif line.startswith("CONFIDENCE:"):
                result["confidence"] = line.split(":", 1)[1].strip().lower()
            elif line.startswith("REASONING:"):
                result["reasoning"] = line.split(":", 1)[1].strip()
            elif line.startswith("WARNING:"):
                warning = line.split(":", 1)[1].strip()
                if warning.upper() != "NONE":
                    result["warning"] = warning

        return result
