"""AI Optimizer — LLM-powered resume bullet point refinement and feedback."""
import os
import logging
from typing import Optional

from google.genai import Client

logger = logging.getLogger(__name__)

# Prompt used for bullet-point optimization
OPTIMIZATION_PROMPT = """
You are a professional career coach and resume writer.
Your task is to transform Weak Bullet Points from a resume into Strong, Impactful, and Metric-Driven sentences.

CRITERIA FOR REFINEMENT:
1. Use strong action verbs (e.g., "Spearheaded", "Optimized", "Engineered").
2. Quantify achievements where possible (add realistic metrics if none are provided, but mark them as placeholders like [X%]).
3. Focus on outcomes/results, not just tasks.
4. Keep the tone professional, concise, and ATS-friendly.

EXAMPLES:
- Weak: "Worked on a React dashboard."
- Strong: "Engineered a high-performance interactive dashboard using React, reducing overall page load time by 40% and improving user retention."

- Weak: "Fixed bugs in Python."
- Strong: "Identified and resolved 150+ critical performance bottlenecks in a legacy Python backend, enhancing system stability by 25%."

NOW REFINE THE FOLLOWING BULLET POINT:
"{bullet_point}"

Respond ONLY with the refined version. No preamble or conversational text.
"""


class AIOptimizer:
    """Uses Gemini API to provide advanced AI refinements for resume content."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-3-flash-preview"):
        self.client: Optional[Client] = None
        self.model_name = model_name
        self.candidate_models = []
        self._prepare_network_env()

        if not api_key:
            return

        # env model first, then safe fallback
        ordered = [model_name, "gemini-3-flash-preview"]
        self.candidate_models = [m for i, m in enumerate(ordered) if m and m not in ordered[:i]]

        try:
            self.client = Client(api_key=api_key)
            logger.info(f"AIOptimizer initialized with preferred model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self.client = None

    def _prepare_network_env(self):
        """Disable inherited proxies that break outbound calls."""
        no_proxy_hosts = [
            "generativelanguage.googleapis.com",
            "googleapis.com",
            "ai.google.dev",
            "127.0.0.1",
            "localhost",
        ]
        existing_no_proxy = os.environ.get("NO_PROXY", "")
        merged = [h for h in existing_no_proxy.split(",") if h.strip()]
        for host in no_proxy_hosts:
            if host not in merged:
                merged.append(host)
        os.environ["NO_PROXY"] = ",".join(merged)
        os.environ["no_proxy"] = os.environ["NO_PROXY"]

    @property
    def is_ready(self) -> bool:
        """Returns True if API key is configured and client initialized."""
        return self.client is not None

    def _generate_text(self, prompt: str) -> Optional[str]:
        """Try configured model first, then fallbacks."""
        if not self.is_ready:
            return None

        last_err = None
        for model in self.candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                text = (response.text or "").strip() if response else ""
                if text:
                    self.model_name = model
                    return text
            except Exception as e:
                last_err = e
                logger.warning(f"Gemini model '{model}' failed, trying next fallback: {e}")

        if last_err:
            logger.error(f"All Gemini model attempts failed: {last_err}")
        return None

    def refine_bullet(self, bullet: str) -> Optional[str]:
        """Uses LLM to refine a single resume bullet point with reversible PII masking."""
        from engine.pii_redactor import PIIRedactor
        redactor = PIIRedactor()
        masked_bullet, mapping = redactor.mask(bullet)

        prompt = OPTIMIZATION_PROMPT.format(bullet_point=masked_bullet)
        response = self._generate_text(prompt)

        if response:
            return redactor.unmask(response, mapping)
        return None

    def refine_bullet_stream(self, bullet: str):
        """
        Uses LLM to refine a single resume bullet point and yields unmasked stream chunks.
        Applies a sliding window buffer to prevent raw PII placeholder fragments from flickering.
        """
        import re
        from engine.pii_redactor import PIIRedactor
        redactor = PIIRedactor()
        masked_bullet, mapping = redactor.mask(bullet)

        prompt = OPTIMIZATION_PROMPT.format(bullet_point=masked_bullet)

        if not self.is_ready:
            yield "Error: AI Optimizer is not configured."
            return

        last_err = None
        for model in self.candidate_models:
            try:
                response_stream = self.client.models.generate_content_stream(
                    model=model,
                    contents=prompt,
                )

                buffer = ""
                incomplete_placeholder_pattern = re.compile(r"\[[A-Z0-9_]*$")

                for chunk in response_stream:
                    text = chunk.text or ""
                    buffer += text

                    match = incomplete_placeholder_pattern.search(buffer)
                    if match:
                        split_idx = match.start()
                        flush_text = buffer[:split_idx]
                        buffer = buffer[split_idx:]
                    else:
                        flush_text = buffer
                        buffer = ""

                    if flush_text:
                        yield redactor.unmask(flush_text, mapping)

                if buffer:
                    yield redactor.unmask(buffer, mapping)

                self.model_name = model
                return

            except Exception as e:
                last_err = e
                logger.warning(f"Streaming failed for model {model}: {e}")

        if last_err:
            logger.error(f"All model streaming attempts failed: {last_err}")
            yield f"Error: AI Engine failed to generate stream: {str(last_err)}"

    def analyze_cv_weaknesses(self, full_text: str) -> Optional[str]:
        """Provides a high-level strategic overview of CV gaps with reversible PII masking."""
        from engine.pii_redactor import PIIRedactor
        redactor = PIIRedactor()
        masked_text, mapping = redactor.mask(full_text)

        prompt = (
            "Analyze the following resume and list 3 strategic improvements to make it more "
            "competitive for top-tier tech roles. Be specific but concise.\n\n"
            f"{masked_text}"
        )
        response = self._generate_text(prompt)

        if response:
            return redactor.unmask(response, mapping)
        return None
