"""Skill extractor — pattern-based skill detection with 45+ skill categories."""
import re
import logging
from typing import List, Dict, Tuple

from engine.taxonomy import get_taxonomy_categories, get_required_skills, resolve_category

logger = logging.getLogger(__name__)

# Comprehensive skill dictionary organized by domain
SKILL_DICTIONARY = {
    # ── Programming Languages ──────────────────────────────────────────
    "python": ["python", "python3", "python 3"],
    "java": ["java", "j2ee", "jdk", "java ee"],
    "javascript": ["javascript", "js", "nodejs", "node.js", "react", "reactjs",
                    "angular", "angularjs", "vue", "vuejs", "typescript"],
    "c++": ["c++", "cpp", "c plus plus"],
    "c#": ["c#", "csharp", "c sharp", "dotnet", ".net"],
    "sql": ["sql", "mysql", "postgresql", "postgres", "rdbms", "sqlite",
            "oracle db", "t-sql", "plsql"],
    "r": ["r programming", "r language", "rstudio", "r studio"],
    "scala": ["scala", "apache spark scala"],
    "go": ["golang", "go programming"],
    "rust": ["rust programming", "rustlang"],
    "php": ["php", "laravel", "symfony"],
    "ruby": ["ruby", "ruby on rails", "rails"],
    "swift": ["swift", "ios development"],
    "kotlin": ["kotlin", "android development"],

    # ── ML / AI ────────────────────────────────────────────────────────
    "machine learning": ["machine learning", "ml", "predictive modeling",
                         "supervised learning", "unsupervised learning"],
    "deep learning": ["deep learning", "neural network", "tensorflow",
                      "pytorch", "keras", "cnn", "rnn", "lstm", "transformer"],
    "nlp": ["nlp", "natural language processing", "text mining",
            "text analytics", "sentiment analysis", "bert", "gpt"],
    "computer vision": ["computer vision", "image processing", "opencv",
                        "image recognition", "object detection", "yolo"],
    "generative ai": ["generative ai", "genai", "large language model", "llm",
                      "chatgpt", "prompt engineering", "langchain"],

    # ── Data Science / Analytics ───────────────────────────────────────
    "data science": ["data science", "data scientist", "analytics"],
    "data analysis": ["data analysis", "exploratory data analysis", "eda",
                      "data analyst", "business intelligence"],
    "data engineering": ["data engineering", "data pipeline", "etl",
                         "data warehouse", "airflow", "dbt"],
    "statistics": ["statistics", "statistical analysis", "hypothesis testing",
                   "regression", "bayesian", "probability"],
    "pandas": ["pandas", "dataframe"],
    "numpy": ["numpy", "numerical computing"],
    "scikit-learn": ["scikit-learn", "sklearn", "scikit learn"],
    "data visualization": ["data visualization", "tableau", "power bi",
                           "matplotlib", "seaborn", "plotly", "d3.js", "looker"],
    "big data": ["big data", "hadoop", "spark", "hive", "kafka",
                 "mapreduce", "presto", "databricks"],

    # ── Cloud & DevOps ─────────────────────────────────────────────────
    "aws": ["aws", "amazon web services", "ec2", "s3", "lambda",
            "sagemaker", "redshift", "dynamodb"],
    "azure": ["azure", "microsoft azure", "azure devops"],
    "gcp": ["gcp", "google cloud", "bigquery", "google cloud platform"],
    "docker": ["docker", "containerization", "dockerfile"],
    "kubernetes": ["kubernetes", "k8s", "helm", "container orchestration"],
    "ci/cd": ["ci/cd", "jenkins", "github actions", "gitlab ci",
              "continuous integration", "continuous deployment"],
    "terraform": ["terraform", "infrastructure as code", "iac",
                  "cloudformation"],
    "linux": ["linux", "ubuntu", "centos", "bash", "shell scripting"],
    "git": ["git", "github", "gitlab", "version control", "bitbucket"],

    # ── Web Development ────────────────────────────────────────────────
    "frontend": ["frontend", "front-end", "html", "css", "responsive design"],
    "backend": ["backend", "back-end", "django", "flask", "express",
                "spring", "fastapi", "nest.js"],
    "api": ["rest api", "restful", "graphql", "microservices",
            "api development", "swagger", "openapi"],
    "database": ["mongodb", "redis", "elasticsearch", "cassandra",
                 "neo4j", "nosql", "firebase"],
    "full stack": ["full stack", "fullstack", "mern", "mean stack"],

    # ── Business & Management ──────────────────────────────────────────
    "project management": ["project management", "pmp", "scrum", "agile",
                           "kanban", "jira", "asana", "trello"],
    "leadership": ["leadership", "team lead", "team management",
                   "people management", "mentoring"],
    "communication": ["communication", "presentation", "public speaking",
                      "stakeholder management"],
    "problem solving": ["problem solving", "critical thinking",
                        "analytical thinking"],

    # ── Finance ────────────────────────────────────────────────────────
    "financial analysis": ["financial analysis", "financial modeling",
                           "forecasting", "budgeting", "valuation"],
    "accounting": ["accounting", "bookkeeping", "gaap", "ifrs",
                   "financial reporting", "audit"],
    "excel": ["excel", "advanced excel", "vba", "pivot tables",
              "vlookup", "macros"],

    # ── Design ─────────────────────────────────────────────────────────
    "graphic design": ["graphic design", "photoshop", "illustrator",
                       "indesign", "canva", "adobe creative suite"],
    "ui/ux": ["user experience", "user interface", "ux design",
              "ui design", "wireframe", "figma", "sketch", "prototype"],

    # ── Sales & Marketing ──────────────────────────────────────────────
    "digital marketing": ["digital marketing", "seo", "sem",
                          "social media marketing", "google analytics",
                          "content marketing", "email marketing"],
    "sales": ["sales", "crm", "salesforce", "lead generation",
              "business development", "account management"],

    # ── HR ─────────────────────────────────────────────────────────────
    "employee relations": ["employee relations", "labor relations",
                           "conflict resolution"],
    "recruitment": ["recruitment", "recruiting", "talent acquisition",
                    "staffing", "hiring", "ats"],
    "benefits administration": ["benefits administration", "compensation",
                                "401k", "employee benefits"],
    "hr compliance": ["compliance", "fmla", "ada", "eeo", "labor law",
                      "employment law", "osha"],
    "performance management": ["performance management", "performance review",
                               "appraisal", "kpi"],
    "training": ["training", "onboarding", "orientation",
                 "learning and development", "l&d"],
    "payroll": ["payroll", "payroll processing", "hris", "workday", "adp"],

    # ── Healthcare ─────────────────────────────────────────────────────
    "healthcare": ["healthcare", "clinical", "patient care", "hipaa",
                   "ehr", "emr", "medical"],
    "nursing": ["nursing", "registered nurse", "rn", "bsn",
                "patient assessment"],

    # ── Engineering ────────────────────────────────────────────────────
    "mechanical engineering": ["mechanical engineering", "cad", "solidworks",
                               "autocad", "ansys", "matlab"],
    "electrical engineering": ["electrical engineering", "circuit design",
                               "pcb", "embedded systems", "fpga", "vhdl"],
    "civil engineering": ["civil engineering", "structural analysis",
                          "construction management"],
}


def _load_core_requirements_from_taxonomy() -> Dict[str, List[str]]:
    """Expose taxonomy requirements for compatibility with existing imports/tests."""
    requirements: Dict[str, List[str]] = {}
    for category in get_taxonomy_categories():
        requirements[category] = get_required_skills(category)
    return requirements


# Dynamic, taxonomy-backed requirements map (24 aligned categories).
CORE_REQUIREMENTS = _load_core_requirements_from_taxonomy()


class SkillExtractor:
    """
    Domain-specific skill extraction using compiled regex patterns.
    Matches against 60+ canonical skill categories with synonym expansion.
    """

    def __init__(self, custom_skills: dict = None):
        self.skill_dict = dict(SKILL_DICTIONARY)
        if custom_skills:
            self.skill_dict.update(custom_skills)

        # Pre-compile regex patterns for performance
        self.skill_patterns = {}
        for canonical, synonyms in self.skill_dict.items():
            pattern = r"\b(" + "|".join(re.escape(s) for s in synonyms) + r")\b"
            self.skill_patterns[canonical] = re.compile(pattern, re.IGNORECASE)

    def extract_skills(self, text: str) -> List[str]:
        """Extract all matching skills from text."""
        if not text or not isinstance(text, str):
            return []
        found = set()
        for skill, pattern in self.skill_patterns.items():
            if pattern.search(text):
                found.add(skill)
        return sorted(list(found))

    def extract_skills_detailed(self, text: str) -> Dict[str, List[str]]:
        """
        Extract skills grouped by domain category.

        Returns:
            Dict mapping domain names to lists of detected skills.
        """
        if not text or not isinstance(text, str):
            return {}

        all_skills = self.extract_skills(text)

        # Group by domain
        domain_map = {
            "Programming Languages": ["python", "java", "javascript", "c++", "c#",
                                      "sql", "r", "scala", "go", "rust", "php",
                                      "ruby", "swift", "kotlin"],
            "AI & Machine Learning": ["machine learning", "deep learning", "nlp",
                                      "computer vision", "generative ai"],
            "Data Science": ["data science", "data analysis", "data engineering",
                             "statistics", "pandas", "numpy", "scikit-learn",
                             "data visualization", "big data"],
            "Cloud & DevOps": ["aws", "azure", "gcp", "docker", "kubernetes",
                               "ci/cd", "terraform", "linux", "git"],
            "Web Development": ["frontend", "backend", "api", "database",
                                "full stack"],
            "Business Skills": ["project management", "leadership",
                                "communication", "problem solving"],
            "Finance": ["financial analysis", "accounting", "excel"],
            "Design": ["graphic design", "ui/ux"],
            "Marketing & Sales": ["digital marketing", "sales"],
            "Human Resources": ["employee relations", "recruitment",
                                "benefits administration", "hr compliance",
                                "performance management", "training", "payroll"],
            "Healthcare": ["healthcare", "nursing"],
            "Engineering": ["mechanical engineering", "electrical engineering",
                            "civil engineering"],
        }

        grouped = {}
        for domain, skills_in_domain in domain_map.items():
            matched = [s for s in all_skills if s in skills_in_domain]
            if matched:
                grouped[domain] = matched

        return grouped

    def calculate_skill_overlap(
        self,
        resume_skills: List[str],
        job_skills: List[str]
    ) -> Tuple[List[str], List[str], float]:
        """
        Calculate overlap between resume skills and job requirements.

        Returns:
            (matched_skills, missing_skills, match_percentage)
        """
        resume_set = set(resume_skills)
        job_set = set(job_skills)
        matched = sorted(list(resume_set & job_set))
        missing = sorted(list(job_set - resume_set))
        match_pct = len(matched) / len(job_set) * 100 if job_set else 0.0
        return matched, missing, match_pct

    def get_category_gap(self, category: str, resume_skills: List[str]) -> Dict:
        """
        Calculate the skills gap for a specific career category.
        """
        target_category = resolve_category(category)
        if not target_category:
            target_category = category.strip().upper() if isinstance(category, str) else "UNKNOWN"

        core_skills = get_required_skills(target_category)
        matched, missing, match_pct = self.calculate_skill_overlap(resume_skills, core_skills)

        return {
            "target_category": target_category,
            "readiness_score": round(match_pct),
            "matched_skills": matched,
            "missing_skills": missing,
            "total_core_skills": len(core_skills)
        }
