"""Taxonomy Unifier — standardizes categories and job titles into 24 unified premium naming conventions."""
import logging
import difflib
from typing import Dict, Optional, Tuple, List
from engine.taxonomy import get_taxonomy_categories, resolve_category

logger = logging.getLogger(__name__)

# Master mapping of 24 canonical category labels (exact ML keys) to their unified, premium naming convention
UNIFIED_TAXONOMY = {
    "ACCOUNTANT": "Accounting",
    "ADVOCATE": "Legal",
    "AGRICULTURE": "Agriculture",
    "APPAREL": "Apparel & Fashion",
    "ARTS": "Arts & Creative Design",
    "AUTOMOBILE": "Automotive",
    "AVIATION": "Aviation",
    "BANKING": "Banking",
    "BPO": "BPO & Customer Support",
    "BUSINESS-DEVELOPMENT": "Business Development",
    "CHEF": "Culinary & Food",
    "CONSTRUCTION": "Construction",
    "CONSULTANT": "Consulting",
    "DESIGNER": "Design",
    "DIGITAL-MEDIA": "Digital Media",
    "ENGINEERING": "Engineering",
    "FINANCE": "Finance",
    "FITNESS": "Fitness & Wellness",
    "HEALTHCARE": "Healthcare",
    "HR": "Human Resources",
    "INFORMATION-TECHNOLOGY": "Software Engineering",
    "PUBLIC-RELATIONS": "Public Relations",
    "SALES": "Sales",
    "TEACHER": "Education & Teaching"
}

# Mapping of common non-standard job categories/titles to canonical keys
LEGACY_MAPPING = {
    "data science": "INFORMATION-TECHNOLOGY",
    "data scientist": "INFORMATION-TECHNOLOGY",
    "web designing": "DESIGNER",
    "devops engineer": "INFORMATION-TECHNOLOGY",
    "network security engineer": "INFORMATION-TECHNOLOGY",
    "pmo": "CONSULTANT",
    "health and fitness": "FITNESS",
    "mechanical engineer": "ENGINEERING",
    "electrical engineering": "ENGINEERING",
    "civil engineer": "CONSTRUCTION",
    "automation testing": "INFORMATION-TECHNOLOGY",
    "dba": "INFORMATION-TECHNOLOGY",
    "hadoop": "INFORMATION-TECHNOLOGY",
    "java developer": "INFORMATION-TECHNOLOGY",
    "dotnet developer": "INFORMATION-TECHNOLOGY",
    "python developer": "INFORMATION-TECHNOLOGY",
    "sap developer": "INFORMATION-TECHNOLOGY",
    "operations manager": "BUSINESS-DEVELOPMENT",
    "dev": "INFORMATION-TECHNOLOGY",
    "coder": "INFORMATION-TECHNOLOGY",
    "software engineer": "INFORMATION-TECHNOLOGY",
    "programmer": "INFORMATION-TECHNOLOGY",
    "accountancy": "ACCOUNTANT",
    "lawyer": "ADVOCATE",
    "law": "ADVOCATE",
    "legal services": "ADVOCATE",
    "farming": "AGRICULTURE",
    "fashion designer": "DESIGNER",
    "artist": "ARTS",
    "creative": "ARTS",
    "mechanic": "AUTOMOBILE",
    "pilot": "AVIATION",
    "banker": "BANKING",
    "customer relations": "BPO",
    "customer care": "BPO",
    "cook": "CHEF",
    "builder": "CONSTRUCTION",
    "civil engineering": "CONSTRUCTION",
    "consulting": "CONSULTANT",
    "ui designer": "DESIGNER",
    "ux designer": "DESIGNER",
    "graphic designer": "DESIGNER",
    "marketing": "DIGITAL-MEDIA",
    "ad agency": "DIGITAL-MEDIA",
    "doctor": "HEALTHCARE",
    "nurse": "HEALTHCARE",
    "recruitment": "HR",
    "recruiter": "HR",
    "publicist": "PUBLIC-RELATIONS",
    "sales representative": "SALES",
    "teacher": "TEACHER",
    "professor": "TEACHER",
    "instructor": "TEACHER",
    "tutor": "TEACHER"
}

class TaxonomyUnifier:
    """
    Standardizes career categories, job titles, and departments into the 24 unified naming conventions.
    Uses:
    1. Exact alias/synonym lookup mapping
    2. Fuzzy match string similarity scoring
    3. LLM semantic fallback (optional)
    """

    def __init__(self, confidence_threshold: float = 0.60):
        self.confidence_threshold = confidence_threshold

    def get_unified_name(self, category_key: str) -> str:
        """Returns the premium unified name for a canonical uppercase category label."""
        return UNIFIED_TAXONOMY.get(category_key.upper().strip(), "General/Other")

    def get_canonical_key(self, unified_name: str) -> Optional[str]:
        """Reverse lookup: returns the canonical uppercase category label for a unified name."""
        cleaned = unified_name.strip().lower()
        for key, val in UNIFIED_TAXONOMY.items():
            if val.strip().lower() == cleaned:
                return key
        return None

    def unify(self, title_or_dept: str) -> str:
        """
        Forces a job title, department, or old category into one of the 24 unified names.
        If confidence is low (below threshold), returns 'General/Other'.
        """
        canonical_key, score = self.classify(title_or_dept)
        if score >= self.confidence_threshold:
            return self.get_unified_name(canonical_key)
        return "General/Other"

    def classify(self, text: str) -> Tuple[str, float]:
        """
        Matches a free-form string to one of the 24 canonical keys.
        Returns:
            (canonical_key, match_score)
        """
        if not text or not isinstance(text, str):
            return "GENERAL", 0.0

        cleaned = text.strip().lower()
        if not cleaned:
            return "GENERAL", 0.0

        # 1. Direct Canonical Check
        canonical_upper = text.strip().upper()
        if canonical_upper in UNIFIED_TAXONOMY:
            return canonical_upper, 1.0

        # 2. Legacy / Special Mapping Check
        if cleaned in LEGACY_MAPPING:
            target_key = LEGACY_MAPPING[cleaned]
            return target_key, 1.0

        # Try mapping sub-parts / direct substring match on legacy keys
        for leg_key, target_key in LEGACY_MAPPING.items():
            if leg_key in cleaned or cleaned in leg_key:
                return target_key, 0.90

        # Try mapping sub-parts / direct substring match on taxonomy aliases
        try:
            from engine.taxonomy import get_taxonomy
            taxonomy = get_taxonomy()
            for alias_key, target_key in taxonomy["alias_to_label"].items():
                if len(alias_key) > 2 and (alias_key in cleaned or cleaned in alias_key):
                    return target_key, 0.90
        except Exception:
            pass

        # 3. Fuzzy String Distance Check using difflib
        best_key = None
        best_score = 0.0

        # Check similarities against canonical keys & unified names
        for canonical, unified in UNIFIED_TAXONOMY.items():
            # Match against canonical string
            ratio = difflib.SequenceMatcher(None, cleaned, canonical.lower().replace("-", " ")).ratio()
            if ratio > best_score:
                best_score = ratio
                best_key = canonical

            # Match against unified string
            ratio_unified = difflib.SequenceMatcher(None, cleaned, unified.lower()).ratio()
            if ratio_unified > best_score:
                best_score = ratio_unified
                best_key = canonical

        # Try to resolve category via taxonomy aliases
        resolved = resolve_category(text)
        if resolved and resolved in UNIFIED_TAXONOMY:
            return resolved, 1.0

        if best_key and best_score >= self.confidence_threshold:
            return best_key, round(best_score, 3)

        return "GENERAL", 0.0
