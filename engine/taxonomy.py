"""Taxonomy loader and helpers for category/skill alignment."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import yaml


DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "config" / "taxonomy.yaml"


@lru_cache(maxsize=1)
def get_taxonomy(taxonomy_path: Optional[Path] = None) -> Dict:
    """Load taxonomy YAML and build fast lookup maps."""
    path = taxonomy_path or DEFAULT_TAXONOMY_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    categories = data.get("categories", [])
    by_label: Dict[str, Dict] = {}
    alias_to_label: Dict[str, str] = {}

    for entry in categories:
        label = (entry.get("label") or "").strip()
        if not label:
            continue
        canonical = label.upper()
        aliases = [a.strip() for a in entry.get("aliases", []) if isinstance(a, str) and a.strip()]
        required_skills = [s.strip().lower() for s in entry.get("required_skills", []) if isinstance(s, str) and s.strip()]

        by_label[canonical] = {
            "label": canonical,
            "aliases": aliases,
            "required_skills": required_skills,
        }

        alias_to_label[canonical.lower()] = canonical
        alias_to_label[canonical.replace("-", " ").lower()] = canonical
        for alias in aliases:
            alias_to_label[alias.lower()] = canonical

    return {
        "version": data.get("version", 1),
        "categories": categories,
        "by_label": by_label,
        "alias_to_label": alias_to_label,
    }


def get_taxonomy_categories() -> List[str]:
    """Return canonical category labels."""
    return sorted(get_taxonomy()["by_label"].keys())


def resolve_category(label: Optional[str]) -> Optional[str]:
    """Resolve a free-form label/alias into canonical taxonomy label."""
    if not label:
        return None
    key = label.strip().lower()
    if not key:
        return None

    # Reverse lookup for unified premium naming convention
    try:
        from engine.taxonomy_unifier import TaxonomyUnifier
        unifier = TaxonomyUnifier()
        canonical_key = unifier.get_canonical_key(label)
        if canonical_key:
            return canonical_key
    except Exception:
        pass

    taxonomy = get_taxonomy()
    return taxonomy["alias_to_label"].get(key)


def get_required_skills(category_label: Optional[str]) -> List[str]:
    """Return required skills for category, or empty list if unknown."""
    canonical = resolve_category(category_label)
    if not canonical:
        return []
    return list(get_taxonomy()["by_label"][canonical]["required_skills"])
