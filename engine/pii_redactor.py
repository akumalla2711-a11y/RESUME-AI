"""PII Redactor — Identifies, masks, and reversibly restores PII inside text payloads."""
import re
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class PIIRedactor:
    """
    Identifies and redacts Personally Identifiable Information (PII) from resumes.
    Redacts:
    - Emails (RFC 5322 compliance pattern)
    - Phone Numbers (International and domestic formats)
    - Physical Addresses (Street level matching & ZIP/PIN codes)
    - Names (via spaCy Named Entity Recognition)
    Supports fully reversible unmasking.
    """

    def __init__(self):
        # Email: Standard RFC 5322 compliance pattern
        self.email_pattern = re.compile(
            r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
        )

        # Phone: International & domestic formats (US standard, international spaced/consecutive 10-digit formats)
        self.phone_pattern = re.compile(
            r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b|"
            r"\b(?:\+?\d{1,3}[-.\s]?)?\d{5}[-.\s]?\d{5}\b|"
            r"\b\d{10}\b"
        )

        # Address: Street level matching + zip/pin codes
        self.street_pattern = re.compile(
            r"\b\d+\s+[A-Za-z0-9\s,.-]+?\s*(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|way|court|ct|apartment|apt|suite|ste|floor|fl|p\.o\.\s*box)\b",
            re.IGNORECASE
        )
        self.zip_pattern = re.compile(
            r"\b\d{5}(?:-\d{4})?\b|\b\d{3}\s?\d{3}\b"
        )

    def mask(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Redacts PII (Emails, Phone Numbers, Addresses, Names) from text.

        Returns:
            (masked_text, mapping_dict)
        """
        if not text or not isinstance(text, str):
            return "", {}

        mapping = {}
        masked_text = text

        # Helper to generate unique placeholder
        def _add_placeholder(category: str, original_value: str) -> str:
            # Check if this original value was already masked to reuse the same placeholder
            for ph, val in mapping.items():
                if val == original_value:
                    return ph
            # Otherwise create a new index
            idx = sum(1 for ph in mapping if ph.startswith(f"[{category}_"))
            placeholder = f"[{category}_{idx}]"
            mapping[placeholder] = original_value
            return placeholder

        # 1. Mask Emails
        def email_repl(match):
            return _add_placeholder("EMAIL", match.group(0))
        masked_text = self.email_pattern.sub(email_repl, masked_text)

        # 2. Mask Phone Numbers
        def phone_repl(match):
            return _add_placeholder("PHONE", match.group(0))
        masked_text = self.phone_pattern.sub(phone_repl, masked_text)

        # 3. Mask Addresses (Street and ZIP/PIN codes)
        def street_repl(match):
            return _add_placeholder("ADDRESS", match.group(0))
        masked_text = self.street_pattern.sub(street_repl, masked_text)

        def zip_repl(match):
            return _add_placeholder("ADDRESS", match.group(0))
        masked_text = self.zip_pattern.sub(zip_repl, masked_text)

        # 4. Mask Names using spaCy NER
        try:
            from engine.text_cleaner import _get_nlp
            nlp = _get_nlp()
            if nlp:
                doc = nlp(masked_text)
                # Find all PERSON entities and sort right-to-left to prevent index shifts
                persons = sorted(
                    [(ent.start_char, ent.end_char, ent.text) for ent in doc.ents if ent.label_ == "PERSON"],
                    key=lambda x: x[0],
                    reverse=True
                )

                # Replace person entities in the text
                for start, end, name_text in persons:
                    cleaned_name = name_text.strip(",. \n")
                    if not cleaned_name or len(cleaned_name) < 2:
                        continue

                    placeholder = _add_placeholder("NAME", cleaned_name)
                    masked_text = masked_text[:start] + placeholder + masked_text[end:]
        except Exception as e:
            logger.warning(f"spaCy NER Name redaction failed: {e}")

        return masked_text, mapping

    def unmask(self, masked_text: str, mapping: Dict[str, str]) -> str:
        """
        Reverses the masking by replacing placeholders with their original values.
        """
        if not masked_text or not mapping:
            return masked_text

        unmasked_text = masked_text
        # Sort placeholders by length descending to prevent substring substitution collisions
        # e.g., replacing [NAME_10] before [NAME_1]
        sorted_placeholders = sorted(mapping.keys(), key=len, reverse=True)

        for placeholder in sorted_placeholders:
            unmasked_text = unmasked_text.replace(placeholder, mapping[placeholder])

        return unmasked_text
