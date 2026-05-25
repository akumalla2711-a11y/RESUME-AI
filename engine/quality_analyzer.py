"""Quality Analyzer — multi-factor resume scoring based on structure, content, and impact."""
import re
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

# Action verbs that indicate strong professional impact
IMPACT_VERBS = {
    "led", "managed", "spearheaded", "developed", "created", "designed",
    "implemented", "integrated", "optimized", "increased", "decreased", "saved",
    "built", "authored", "mentored", "orchestrated", "transformed", "shipped",
    "launched", "migrated", "automated", "streamlined", "accelerated"
}

# Standard resume section headers
SECTION_PATTERNS = {
    "experience": r"\b(experience|work history|employment|career summary)\b",
    "education": r"\b(education|academic|qualifications|certifications)\b",
    "projects": r"\b(projects|technical projects|portfolio|key projects)\b",
    "skills": r"\b(skills|technical skills|technologies|expertise)\b",
    "summary": r"\b(professional summary|profile|about me|objective)\b",
}

class QualityAnalyzer:
    """Analyzes resume text to compute a granular quality breakdown."""

    def analyze(self, raw_text: str, skills_count: int) -> Dict:
        """
        Perform multi-factor analysis on the resume text.
        
        Returns:
            Dict containing scores for formatting, content_depth, impact, and skills_density.
        """
        text_lower = raw_text.lower()
        word_count = len(text_lower.split())
        
        # 1. Section Detection (Structure Score)
        sections_found = []
        for section, pattern in SECTION_PATTERNS.items():
            if re.search(pattern, text_lower):
                sections_found.append(section)
        
        structure_score = (len(sections_found) / len(SECTION_PATTERNS)) * 100
        
        # 2. Impact Verbs (Impact Score)
        impact_count = 0
        for verb in IMPACT_VERBS:
            # Simple word-boundary check
            matches = re.findall(r"\b" + verb + r"\b", text_lower)
            impact_count += len(matches)
        
        # Normalize impact: 1 verb per 100 words is decent, 5 verbs total is good
        impact_score = min((impact_count / 8) * 100, 100) if impact_count > 0 else 0
        
        # 3. Content Depth (Length & Density)
        # 300-600 words is ideal for a resume
        if 300 <= word_count <= 800:
            depth_score = 100
        elif word_count < 300:
            depth_score = (word_count / 300) * 100
        else:
            depth_score = 80 # Penalty for being TOO long
            
        # 4. Skills Density
        # Aim for 5-15% of the text being detected as skills
        density_pct = (skills_count / word_count) * 100 if word_count > 0 else 0
        if 4 <= density_pct <= 12:
            density_score = 100
        else:
            density_score = min((density_pct / 4) * 100, 100)

        # 5. Build detailed breakdown
        detailed = {
            "structure": {
                "score": round(structure_score),
                "label": "Formatting & Structure",
                "feedback": f"Found {len(sections_found)} essential sections.",
                "missing": [s for s in SECTION_PATTERNS.keys() if s not in sections_found]
            },
            "impact": {
                "score": round(impact_score),
                "label": "Action Verb Impact",
                "feedback": f"Used {impact_count} strong action verbs."
            },
            "depth": {
                "score": round(depth_score),
                "label": "Content Depth",
                "feedback": f"Total length: {word_count} words."
            },
            "skills": {
                "score": round(density_score),
                "label": "Skills Density",
                "feedback": f"Skills make up {round(density_pct, 1)}% of your content."
            }
        }
        
        # Calculate Weighted Final Score
        # 30% Structure, 25% Impact, 20% Depth, 25% Skills
        final_score = (
            (structure_score * 0.30) +
            (impact_score * 0.25) +
            (depth_score * 0.20) +
            (density_score * 0.25)
        )
        
        return {
            "final_score": round(final_score),
            "breakdown": detailed,
            "summary": self._generate_summary(detailed)
        }

    def _generate_summary(self, detailed: Dict) -> str:
        score = detailed["structure"]["score"]
        if score < 60:
            return "Consider adding more standard sections like projects or education."
        if detailed["impact"]["score"] < 40:
            return "Add more action verbs (e.g., 'Led', 'Optimized') to show impact."
        return "Your resume is well-structured and uses strong professional language."
