"""Truncation manager — prioritized section-level resume truncation."""
import re
import logging
from typing import Dict, List, Set
from engine.token_utils import estimate_tokens_local

logger = logging.getLogger(__name__)

# Section headers regex mapping
SECTION_HEADERS = {
    "references": re.compile(r"\b(?:references|recommendations|referees)\b", re.IGNORECASE),
    "interests": re.compile(r"\b(?:interests|hobbies|extracurriculars|activities)\b", re.IGNORECASE),
    "summary": re.compile(r"\b(?:summary|objective|profile|about me|professional summary)\b", re.IGNORECASE),
    "projects": re.compile(r"\b(?:projects|academic projects|personal projects|key projects)\b", re.IGNORECASE),
    "certifications": re.compile(r"\b(?:certifications|certificates|courses|awards|achievements)\b", re.IGNORECASE),
    "education": re.compile(r"\b(?:education|academic background|studies|degrees)\b", re.IGNORECASE),
    "skills": re.compile(r"\b(?:skills|technical skills|competencies|expertise|proficiencies)\b", re.IGNORECASE),
    "experience": re.compile(r"\b(?:experience|work history|employment|professional background|career history|work experience)\b", re.IGNORECASE),
}

# Ordered from lowest priority (dropped first) to highest priority (kept last)
TRUNCATION_ORDER = [
    "references",
    "interests",
    "summary",
    "projects",
    "certifications",
    "education",
    "skills",
    "experience"
]


def split_resume_into_sections(text: str) -> Dict[str, str]:
    """
    Parses raw resume text and groups content into structural sections.
    """
    sections = {sec: "" for sec in TRUNCATION_ORDER}
    sections["header"] = ""  # For contact info/intro text before first section

    current_section = "header"
    lines = text.split("\n")

    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line:
            if sections[current_section]:
                sections[current_section] += "\n"
            continue

        # Check if line looks like a new section header
        is_header = False
        if len(cleaned_line) < 30:
            for sec_name, pattern in SECTION_HEADERS.items():
                if pattern.search(cleaned_line):
                    current_section = sec_name
                    is_header = True
                    break

        # Append line to active section
        if not is_header:
            if sections[current_section]:
                sections[current_section] += "\n" + line
            else:
                sections[current_section] = line
        else:
            if sections[current_section]:
                sections[current_section] += "\n\n" + line
            else:
                sections[current_section] = line

    return sections


def assemble_remaining(sections: Dict[str, str], dropped: Set[str]) -> str:
    """Reassembles the non-dropped sections in a logical resume flow."""
    parts = []
    if sections.get("header") and sections["header"].strip():
        parts.append(sections["header"].strip())

    logical_order = ["summary", "skills", "experience", "education", "projects", "certifications", "interests", "references"]
    for sec in logical_order:
        if sec not in dropped and sections.get(sec) and sections[sec].strip():
            parts.append(sections[sec].strip())

    return "\n\n".join(parts)


def truncate_resume_to_budget(text: str, token_limit: int = 4000) -> str:
    """
    Progressively drops low-priority sections if the estimated token count exceeds the limit.
    """
    if not text:
        return ""

    if estimate_tokens_local(text) <= token_limit:
        return text

    sections = split_resume_into_sections(text)

    # Progressively drop sections from lowest to highest priority
    dropped_sections = set()
    for sec_to_drop in TRUNCATION_ORDER:
        if sec_to_drop in {"skills", "experience"}:
            break  # Never drop core skills or experience

        dropped_sections.add(sec_to_drop)

        # Assemble and test remaining size
        assembled_text = assemble_remaining(sections, dropped_sections)
        if estimate_tokens_local(assembled_text) <= token_limit:
            logger.info(f"Resume truncated under budget ({token_limit} tokens) by dropping: {sorted(list(dropped_sections))}")
            return assembled_text

    # If still over budget, return the minimum retained structural blocks
    return assemble_remaining(sections, dropped_sections)
