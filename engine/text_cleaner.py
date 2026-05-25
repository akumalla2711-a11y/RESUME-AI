"""Text cleaner — spaCy-based NLP pipeline for resume text preprocessing."""
import logging
import re

import spacy

logger = logging.getLogger(__name__)

# Module-level singleton to avoid reloading spaCy model
_nlp_instance = None


def _get_nlp(model_name: str = "en_core_web_sm"):
    """Lazy-load spaCy model (singleton)."""
    global _nlp_instance
    if _nlp_instance is None:
        logger.info(f"Loading spaCy model: {model_name}")
        _nlp_instance = spacy.load(model_name)
        logger.info("spaCy model loaded successfully")
    return _nlp_instance


class TextCleaner:
    """
    Resume text cleaner with spaCy NLP pipeline.
    Extracted from the original notebook's ResumeCleaner class.
    """

    def __init__(self, spacy_model: str = "en_core_web_sm"):
        self.nlp = _get_nlp(spacy_model)
        self.url_pattern = re.compile(r"http\S+")
        self.email_pattern = re.compile(r"\S+@\S+")
        self.special_chars_pattern = re.compile(r"[^a-z0-9\s]")
        self.newline_pattern = re.compile(r"\n")
        self.nbsp_pattern = re.compile(r"\xa0")
        self.whitespace_pattern = re.compile(r"\s+")
        self.html_tag_pattern = re.compile(r"<[^>]+>")

    def clean(self, text: str) -> str:
        """
        Clean a single resume text.

        Steps:
        1. Lowercase
        2. Remove URLs, emails, HTML tags
        3. Remove special characters
        4. Normalize whitespace
        5. spaCy lemmatization (remove stop words, punctuation, short tokens, digits)

        Returns:
            Cleaned, lemmatized text
        """
        if not isinstance(text, str) or not text.strip():
            return ""

        text = text.lower()
        text = self.html_tag_pattern.sub(" ", text)
        text = self.url_pattern.sub(" ", text)
        text = self.email_pattern.sub(" ", text)
        text = self.special_chars_pattern.sub(" ", text)
        text = self.newline_pattern.sub(" ", text)
        text = self.nbsp_pattern.sub(" ", text)
        text = self.whitespace_pattern.sub(" ", text).strip()

        if len(text) < 10:
            return ""

        doc = self.nlp(text)
        cleaned_tokens = [
            token.lemma_
            for token in doc
            if not token.is_stop
            and not token.is_punct
            and len(token.text) > 2
            and not token.text.isdigit()
        ]
        return " ".join(cleaned_tokens)

    def extract_raw_skills_text(self, text: str) -> str:
        """
        Light cleaning for skill extraction (preserves more context).
        Does NOT lemmatize — keeps original words for pattern matching.
        """
        if not isinstance(text, str) or not text.strip():
            return ""
        text = text.lower()
        text = self.html_tag_pattern.sub(" ", text)
        text = self.whitespace_pattern.sub(" ", text).strip()
        return text
