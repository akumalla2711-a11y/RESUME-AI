"""Job matcher — matches a resume against the jobs database using TF-IDF + skill overlap."""
import json
import logging
import time
from pathlib import Path
from typing import List, Dict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from engine.skill_extractor import SkillExtractor
from engine.text_cleaner import TextCleaner

logger = logging.getLogger(__name__)


class JobMatcher:
    """
    Matches a cleaned resume against a jobs database.
    Uses TF-IDF cosine similarity + skill-based scoring for hybrid ranking.
    """

    def __init__(self, skill_weight: float = 0.35):
        self.skill_weight = skill_weight
        self.skill_extractor = SkillExtractor()
        self.text_cleaner = TextCleaner()
        self.jobs = []
        self.job_vectors = None
        self.vectorizer = None
        self.is_ready = False

    def load_jobs(self, jobs_path: Path):
        """Load jobs database from JSON."""
        logger.info(f"Loading jobs database from {jobs_path}")
        with open(jobs_path, "r", encoding="utf-8") as f:
            self.jobs = json.load(f)

        # Standardize job categories using TaxonomyUnifier
        from engine.taxonomy_unifier import TaxonomyUnifier
        unifier = TaxonomyUnifier()
        for job in self.jobs:
            if "category" in job:
                job["category"] = unifier.unify(job["category"])

        logger.info(f"Loaded {len(self.jobs)} jobs/internships")
        self._build_index()

    def _build_index(self):
        """Build TF-IDF index over all job descriptions."""
        if not self.jobs:
            logger.warning("No jobs loaded, cannot build index")
            return

        # Combine job description + required skills + title for richer matching
        job_texts = []
        for job in self.jobs:
            combined = " ".join([
                job.get("title", ""),
                job.get("description", ""),
                " ".join(job.get("required_skills", [])),
                " ".join(job.get("preferred_skills", [])),
                job.get("category", ""),
            ])
            cleaned = self.text_cleaner.clean(combined)
            job_texts.append(cleaned)

        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            stop_words="english",
            min_df=1,
            max_df=0.95,
        )
        self.job_vectors = self.vectorizer.fit_transform(job_texts)
        self.is_ready = True
        logger.info(f"Job index built: {self.job_vectors.shape}")

    def match(
        self,
        cleaned_resume: str,
        raw_resume: str,
        predicted_categories: List[str] = None,
        top_n: int = 15,
        min_score: float = 10.0,
    ) -> List[Dict]:
        """
        Match a resume against the jobs database.

        Args:
            cleaned_resume: Lemmatized/cleaned resume text
            raw_resume: Original resume text (for skill extraction)
            predicted_categories: Top predicted resume categories (for boosting)
            top_n: Number of results to return
            min_score: Minimum combined score threshold

        Returns:
            List of job matches with scores, sorted by combined score
        """
        if not self.is_ready:
            raise ValueError("JobMatcher not ready. Load jobs first.")

        # --- TF-IDF similarity ---
        resume_vector = self.vectorizer.transform([cleaned_resume])
        tfidf_scores = cosine_similarity(resume_vector, self.job_vectors).flatten()

        # --- Skill overlap ---
        resume_skills = self.skill_extractor.extract_skills(raw_resume.lower())
        skill_scores = np.zeros(len(self.jobs))
        skill_details = []

        for idx, job in enumerate(self.jobs):
            job_skills = job.get("required_skills", []) + job.get("preferred_skills", [])
            matched, missing, match_pct = self.skill_extractor.calculate_skill_overlap(
                resume_skills, job_skills
            )
            skill_scores[idx] = match_pct / 100.0
            skill_details.append({"matched": matched, "missing": missing})

        # --- Category boost ---
        category_boost = np.zeros(len(self.jobs))
        if predicted_categories:
            for idx, job in enumerate(self.jobs):
                job_cat = job.get("category", "").lower()
                for rank, pred_cat in enumerate(predicted_categories):
                    if pred_cat.lower() == job_cat:
                        # Higher boost for first predicted category
                        category_boost[idx] = 0.1 * (1.0 - rank * 0.3)
                        break

        # --- Combined score ---
        combined = (
            (1 - self.skill_weight) * tfidf_scores
            + self.skill_weight * skill_scores
            + category_boost
        )
        combined_pct = np.round(combined * 100, 2)

        # --- Build results ---
        results = []
        sorted_indices = np.argsort(combined_pct)[::-1]

        for rank, idx in enumerate(sorted_indices[:top_n * 2], start=1):
            score = float(combined_pct[idx])
            if score < min_score:
                continue

            job = self.jobs[idx]
            results.append({
                "rank": rank,
                "job_id": job.get("id", f"job-{idx}"),
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "type": job.get("type", "full-time"),
                "category": job.get("category", ""),
                "location": job.get("location", ""),
                "experience_level": job.get("experience_level", ""),
                "salary_range": job.get("salary_range", ""),
                "description": job.get("description", "")[:300],
                "apply_url": job.get("apply_url", "#"),
                "combined_score": score,
                "tfidf_score": round(float(tfidf_scores[idx]) * 100, 2),
                "skill_score": round(float(skill_scores[idx]) * 100, 2),
                "matched_skills": skill_details[idx]["matched"],
                "missing_skills": skill_details[idx]["missing"],
            })

            if len(results) >= top_n:
                break

        return results

    def rank_live_jobs(
        self,
        cleaned_resume: str,
        resume_skills: List[str],
        live_jobs: List[Dict],
        analysis_categories: List[str],
        skill_weight: float = None,
        time_budget_seconds: float = 5.0,
        description_char_limit: int = 1500,
    ) -> tuple[List[Dict], bool]:
        """
        Re-rank live API jobs using hybrid score with a strict latency budget.

        Returns:
            (ranked_jobs, ranking_budget_exceeded)
        """
        if not live_jobs:
            return [], False

        start = time.perf_counter()
        effective_skill_weight = self.skill_weight if skill_weight is None else skill_weight
        top_category = (analysis_categories[0] if analysis_categories else "").lower()

        # Build ranking corpus
        corpus = []
        for job in live_jobs:
            if (time.perf_counter() - start) > time_budget_seconds:
                return live_jobs, True
            title = (job.get("title") or "").strip()
            desc = (job.get("description") or "")[:description_char_limit]
            required = " ".join(job.get("required_skills", [])[:20])
            category = (job.get("category") or "").strip()
            corpus.append(f"{title} {desc} {required} {category}".strip())

        if not any(corpus):
            return live_jobs, False

        # Lightweight per-request vectorizer for live payload
        ranking_vectorizer = TfidfVectorizer(
            max_features=3000,
            ngram_range=(1, 2),
            stop_words="english",
            min_df=1,
            max_df=0.98,
        )

        if (time.perf_counter() - start) > time_budget_seconds:
            return live_jobs, True

        job_matrix = ranking_vectorizer.fit_transform(corpus)
        resume_vector = ranking_vectorizer.transform([cleaned_resume])
        tfidf_scores = cosine_similarity(resume_vector, job_matrix).flatten()

        if (time.perf_counter() - start) > time_budget_seconds:
            return live_jobs, True

        scored_jobs = []
        for idx, job in enumerate(live_jobs):
            if (time.perf_counter() - start) > time_budget_seconds:
                return live_jobs, True

            job_skills = (job.get("required_skills") or [])[:20]
            matched, missing, match_pct = self.skill_extractor.calculate_skill_overlap(
                resume_skills, job_skills
            )
            skill_score = match_pct / 100.0
            tfidf_score = float(tfidf_scores[idx]) if idx < len(tfidf_scores) else 0.0

            # Category boost from title/description/category text
            boost = 0.0
            if top_category:
                searchable = " ".join([
                    (job.get("title") or ""),
                    (job.get("description") or "")[:description_char_limit],
                    (job.get("category") or ""),
                ]).lower()
                if top_category in searchable:
                    boost = 0.10

            combined = ((1 - effective_skill_weight) * tfidf_score) + (effective_skill_weight * skill_score) + boost
            combined_pct = round(min(max(combined * 100.0, 0.0), 99.0), 2)

            ranked = dict(job)
            ranked["matched_skills"] = matched
            ranked["missing_skills"] = missing
            ranked["tfidf_score"] = round(tfidf_score * 100.0, 2)
            ranked["skill_score"] = round(skill_score * 100.0, 2)
            ranked["combined_score"] = combined_pct
            scored_jobs.append(ranked)

        scored_jobs.sort(key=lambda x: x.get("combined_score", 0.0), reverse=True)
        return scored_jobs, False
