"""Application configuration for Resume Analyzer."""
import os
from pathlib import Path

# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "resume-analyzer-dev-key-2024")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB max upload
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "doc"}
    TRUSTED_DOMAINS = [
        "http://127.0.0.1:5000",
        "http://localhost:5000",
    ]
    # Inject production origins from env if present
    _prod_origins = os.environ.get("ALLOWED_CORS_ORIGINS", "")
    if _prod_origins:
        for _origin in _prod_origins.split(","):
            _cleaned = _origin.strip()
            if _cleaned and _cleaned not in TRUSTED_DOMAINS:
                TRUSTED_DOMAINS.append(_cleaned)

    MODEL_DIR = BASE_DIR / "models"
    DATA_DIR = BASE_DIR / "data"
    TAXONOMY_PATH = BASE_DIR / "config" / "taxonomy.yaml"
    JOBS_DB_PATH = DATA_DIR / "jobs_database.json"
    SPACY_MODEL = "en_core_web_sm"
    TOP_N_RECOMMENDATIONS = 100
    MIN_SCORE_THRESHOLD = 5.0
    SKILL_WEIGHT = 0.35
    LOW_CONFIDENCE_THRESHOLD = 0.30
    CATEGORY_NEAR_TIE_DELTA = 0.05
    RANKING_TIME_BUDGET_SECONDS = 5.0
    RANKING_DESC_CHAR_LIMIT = 1500
    OPTIMIZE_RATE_LIMIT = os.environ.get("OPTIMIZE_RATE_LIMIT", "20 per hour")
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'data' / 'resumeai.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JSearch API (RapidAPI)
    JSEARCH_API_KEY = os.environ.get("JSEARCH_API_KEY", "")

    # Email (Gmail SMTP)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_FROM_NAME = os.environ.get("MAIL_FROM_NAME", "ResumeAI")

    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # Gemini AI (for optimization)
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL_NAME", "gemini-3-flash-preview")

    # Twilio SMS
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")

class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-in-production")


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)()
