"""
Resume Analyzer & Job Recommender - Flask Web Application
Upload your resume to get AI-powered skill analysis and job recommendations.
"""
import csv
import io
import json
import logging
import os
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_login import LoginManager, current_user, login_required
from werkzeug.exceptions import RequestEntityTooLarge

from auth import auth_bp
from config import get_config
from engine.ai_optimizer import AIOptimizer
from engine.category_predictor import CategoryPredictor
from engine.email_service import send_application_email
from engine.job_api import fetch_real_jobs
from engine.job_matcher import JobMatcher
from engine.network_utils import bypass_proxies
from engine.quality_analyzer import QualityAnalyzer
from engine.resume_parser import parse_resume
from engine.skill_extractor import SkillExtractor
from engine.taxonomy import get_taxonomy_categories, resolve_category
from engine.text_cleaner import TextCleaner
from models import (
    Application,
    ApplicationStatus,
    CategoryFeedback,
    Employer,
    HiringStage,
    JobPosting,
    ResumeAnalysis,
    SavedJob,
    User,
    UserPreference,
    db,
)

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except Exception:  # pragma: no cover
    Limiter = None
    get_remote_address = None


# Clear problematic proxy environment variables on startup
bypass_proxies()


# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("resume_processing.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# App config
app = Flask(__name__)
cfg = get_config()
app.config["MAX_CONTENT_LENGTH"] = cfg.MAX_CONTENT_LENGTH
app.config["SECRET_KEY"] = cfg.SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = cfg.SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = cfg.SQLALCHEMY_TRACK_MODIFICATIONS
CORS(app, origins=cfg.TRUSTED_DOMAINS)


@app.errorhandler(RequestEntityTooLarge)
def request_entity_too_large(_error):
    return jsonify({"error": "File is too large. Maximum upload size is 10 MB."}), 413


@app.after_request
def add_header(r):
    """
    Force latest JS/CSS files to load without browser caching.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r



def _rate_limit_key():
    if current_user.is_authenticated:
        return f"user:{current_user.id}"
    if get_remote_address is None:
        return "ip:unknown"
    return f"ip:{get_remote_address()}"


if Limiter is not None:
    limiter = Limiter(
        key_func=_rate_limit_key,
        app=app,
        default_limits=[],
        storage_uri=cfg.RATELIMIT_STORAGE_URI,
    )
    
    from flask_limiter import RateLimitExceeded
    @app.errorhandler(RateLimitExceeded)
    def ratelimit_handler(e):
        return jsonify({
            "success": False,
            "error": "Too many requests. Please wait a moment before trying again."
        }), 429
else:
    logger.warning("flask-limiter not available; optimizer rate limiting disabled.")

    class _NoopLimiter:
        @staticmethod
        def limit(*_args, **_kwargs):
            def _decorator(func):
                return func

            return _decorator

    limiter = _NoopLimiter()


# Database
_db_ready = False
db.init_app(app)


# Login
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"error": "Please log in to access this feature.", "auth_required": True}), 401


# Register blueprints
app.register_blueprint(auth_bp)
# emp_bp is registered after its definition below


# ── Seed default hiring stages ────────────────────────────────────────────────
with app.app_context():
    db.create_all()
    _db_ready = True
    logger.info("Database initialized.")

    # Seed hiring stages if not already present
    default_stages = [
        ("Applied", 1, "#6c757d"),
        ("Screening", 2, "#0d6efd"),
        ("Interview", 3, "#ffc107"),
        ("Offer", 4, "#20c997"),
        ("Hired", 5, "#198754"),
        ("Rejected", 6, "#dc3545"),
    ]
    for name, order, color in default_stages:
        existing = HiringStage.query.filter_by(name=name).first()
        if not existing:
            db.session.add(HiringStage(name=name, order=order, color=color))
    db.session.commit()
    logger.info("Hiring stages seeded.")


# Lazy ML components
_text_cleaner = None
_skill_extractor = None
_job_matcher = None
_category_predictor = None
_quality_analyzer = None
_ai_optimizer = None


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _get_text_cleaner():
    global _text_cleaner
    if _text_cleaner is None:
        logger.info("Initializing TextCleaner...")
        _text_cleaner = TextCleaner(cfg.SPACY_MODEL)
    return _text_cleaner


def _get_skill_extractor():
    global _skill_extractor
    if _skill_extractor is None:
        logger.info("Initializing SkillExtractor...")
        _skill_extractor = SkillExtractor()
    return _skill_extractor


def _get_job_matcher():
    global _job_matcher
    if _job_matcher is None:
        logger.info("Initializing JobMatcher...")
        _job_matcher = JobMatcher(skill_weight=cfg.SKILL_WEIGHT)
        _job_matcher.load_jobs(cfg.JOBS_DB_PATH)
    return _job_matcher


def _get_category_predictor():
    global _category_predictor
    if _category_predictor is None:
        logger.info("Initializing CategoryPredictor...")
        _category_predictor = CategoryPredictor()
        _category_predictor.load(cfg.MODEL_DIR)
        if _category_predictor.is_ready:
            model_labels = set(_category_predictor.category_names or [])
            taxonomy_labels = set(get_taxonomy_categories())
            if model_labels != taxonomy_labels:
                missing_in_taxonomy = sorted(model_labels - taxonomy_labels)
                missing_in_model = sorted(taxonomy_labels - model_labels)
                raise RuntimeError(
                    "Taxonomy/model category mismatch. "
                    f"missing_in_taxonomy={missing_in_taxonomy}, "
                    f"missing_in_model={missing_in_model}"
                )
    return _category_predictor


def _get_quality_analyzer():
    global _quality_analyzer
    if _quality_analyzer is None:
        logger.info("Initializing QualityAnalyzer...")
        _quality_analyzer = QualityAnalyzer()
    return _quality_analyzer


def _get_ai_optimizer():
    global _ai_optimizer
    if _ai_optimizer is None:
        logger.info(f"Initializing AIOptimizer with model: {cfg.GEMINI_MODEL_NAME}...")
        _ai_optimizer = AIOptimizer(api_key=cfg.GEMINI_API_KEY, model_name=cfg.GEMINI_MODEL_NAME)
    return _ai_optimizer


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in cfg.ALLOWED_EXTENSIONS


def jwt_required(f):
    """
    Security Middleware: Enforces JSON Web Token (JWT) validation.
    Checks Authorization: Bearer <JWT> header, falls back to cookie sessions,
    and returns 401 on failure.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            from engine.security import decode_jwt_token
            payload = decode_jwt_token(token, app.config["SECRET_KEY"])
            if payload:
                user_id = payload.get("user_id")
                from models import User
                user = User.query.get(user_id)
                if user:
                    from flask_login import login_user
                    login_user(user)
                    return f(*args, **kwargs)
            return jsonify({"error": "Invalid or expired JSON Web Token."}), 401

        # Fallback to standard cookie session
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required. Please sign in or provide a valid JWT."}), 401

        return f(*args, **kwargs)
    return decorated


@app.route("/api/auth/token", methods=["GET", "POST"])
def get_auth_token():
    """
    Exposes secure cryptographic JWT generation for API interactions and testing.
    GET: Resolves active Flask session.
    POST: Resolves standard JSON credentials.
    """
    if request.method == "POST":
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email and password are required."}), 400

        from models import User
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return jsonify({"error": "Invalid email or password."}), 401
    else:
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required to fetch token."}), 401
        user = current_user

    from engine.security import generate_jwt_token
    token = generate_jwt_token(user.id, app.config["SECRET_KEY"])
    return jsonify({
        "success": True,
        "token": token,
        "expires_in": 3600,
        "token_type": "Bearer"
    })


def _get_user_preference(user_id: int):
    return UserPreference.query.filter_by(user_id=user_id).first()


def _set_user_preference(user_id: int, category: str, source: str = "user_confirmation"):
    pref = _get_user_preference(user_id)
    if pref is None:
        pref = UserPreference(user_id=user_id, preferred_category=category, source=source)
        db.session.add(pref)
    else:
        pref.preferred_category = category
        pref.source = source
    db.session.commit()


def _append_correction_csv(record: dict):
    csv_path = cfg.DATA_DIR / "user_corrections.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = csv_path.exists()
    fieldnames = [
        "created_at",
        "user_id",
        "predicted_category",
        "predicted_confidence",
        "confirmed_category",
        "cleaned_resume_text",
    ]
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "created_at": record.get("created_at"),
            "user_id": record.get("user_id"),
            "predicted_category": record.get("predicted_category"),
            "predicted_confidence": record.get("predicted_confidence"),
            "confirmed_category": record.get("confirmed_category"),
            "cleaned_resume_text": record.get("cleaned_resume_text"),
        })


def _log_category_feedback(
    user_id: int,
    predicted_category: str,
    predicted_confidence: float,
    confirmed_category: str,
    cleaned_resume_text: str,
):
    feedback = CategoryFeedback(
        user_id=user_id,
        predicted_category=predicted_category,
        predicted_confidence=predicted_confidence,
        confirmed_category=confirmed_category,
        cleaned_resume_text=cleaned_resume_text,
    )
    db.session.add(feedback)
    db.session.commit()
    _append_correction_csv({
        "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
        "user_id": feedback.user_id,
        "predicted_category": feedback.predicted_category,
        "predicted_confidence": feedback.predicted_confidence,
        "confirmed_category": feedback.confirmed_category,
        "cleaned_resume_text": feedback.cleaned_resume_text,
    })


# Fail fast at startup for taxonomy parity
try:
    _get_category_predictor()
except Exception as startup_err:
    logger.critical(f"Startup parity check failed: {startup_err}")
    raise


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login")
def login_page():
    if current_user.is_authenticated:
        from flask import redirect, url_for

        return redirect(url_for("index"))
    return render_template("login.html", google_client_id=cfg.GOOGLE_CLIENT_ID)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "message": "Resume Analyzer is running"})


@app.route("/api/categories")
def categories():
    predictor = _get_category_predictor()
    cats = predictor.category_names if predictor.is_ready else []
    return jsonify({"categories": cats or []})


@app.route("/api/analyze", methods=["POST"])
@limiter.limit("10 per minute", key_func=_rate_limit_key)
@jwt_required
def analyze():
    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded. Please select a resume file."}), 400

    file = request.files["resume"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not _allowed_file(file.filename):
        return jsonify({
            "error": f"Unsupported file type. Please upload: {', '.join(cfg.ALLOWED_EXTENSIONS)}"
        }), 400

    confirmed_category_input = request.form.get("confirmed_category")
    remember_category = _parse_bool(request.form.get("remember_category"), default=False)

    try:
        logger.info(f"Analyzing resume: {file.filename}")
        raw_text = parse_resume(io.BytesIO(file.read()), file.filename)

        # Strip scripting exploits or HTML tags from parsed resume contents
        from engine.security import sanitize_input_text
        raw_text = sanitize_input_text(raw_text)

        cleaner = _get_text_cleaner()
        cleaned_text = cleaner.clean(raw_text)
        light_cleaned = cleaner.extract_raw_skills_text(raw_text)

        if not cleaned_text:
            return jsonify({
                "error": "Could not extract meaningful content from the resume. "
                         "Please check the file is not empty or image-based."
            }), 400

        extractor = _get_skill_extractor()
        skills_flat = extractor.extract_skills(light_cleaned)
        skills_grouped = extractor.extract_skills_detailed(light_cleaned)

        predictor = _get_category_predictor()
        predicted_details = predictor.predict_with_details(cleaned_text, top_n=3)
        from engine.taxonomy_unifier import TaxonomyUnifier, UNIFIED_TAXONOMY
        unifier = TaxonomyUnifier()
        predicted_categories = [
            {
                "category": unifier.get_unified_name(d["category"]),
                "confidence": d["confidence"],
                "raw_score": d.get("raw_score", d["confidence"]),
                "method": d.get("method", predictor.mode or "fallback"),
            }
            for d in predicted_details
        ]

        top_prediction = predicted_categories[0] if predicted_categories else {
            "category": "General/Other",
            "confidence": 0.5,
            "raw_score": 0.5,
            "method": "fallback",
        }
        top_confidence = float(top_prediction.get("confidence", 0.5))
        second_confidence = float(predicted_categories[1]["confidence"]) if len(predicted_categories) > 1 else 0.0
        low_confidence = top_confidence < cfg.LOW_CONFIDENCE_THRESHOLD
        near_tie = (top_confidence - second_confidence) <= cfg.CATEGORY_NEAR_TIE_DELTA if len(predicted_categories) > 1 else False
        classification_state = "low_confidence" if low_confidence else "high_confidence"
        confirmation_choices = [p["category"] for p in predicted_categories[:3]]

        valid_categories = set(UNIFIED_TAXONOMY.values())
        confirmed_category = unifier.unify(confirmed_category_input) if confirmed_category_input else None
        if confirmed_category_input and confirmed_category == "General/Other" and confirmed_category_input.lower() not in ["general", "other", "general/other"]:
            return jsonify({
                "error": "Invalid confirmed_category value.",
                "confirmation_choices": confirmation_choices,
            }), 400

        analysis_category = top_prediction["category"]
        confirmation_used = False
        preference_applied = False

        if confirmed_category:
            analysis_category = confirmed_category
            confirmation_used = True
            try:
                _log_category_feedback(
                    user_id=current_user.id,
                    predicted_category=top_prediction["category"],
                    predicted_confidence=top_confidence,
                    confirmed_category=confirmed_category,
                    cleaned_resume_text=cleaned_text,
                )
            except Exception as feedback_err:
                logger.warning(f"Failed to persist category feedback: {feedback_err}")

            if remember_category:
                try:
                    _set_user_preference(current_user.id, confirmed_category, source="user_confirmation")
                except Exception as pref_err:
                    logger.warning(f"Failed to save user preference: {pref_err}")
        else:
            user_pref = _get_user_preference(current_user.id)
            if user_pref and user_pref.preferred_category in valid_categories and (low_confidence or near_tie):
                analysis_category = user_pref.preferred_category
                preference_applied = True

        live_jobs = fetch_real_jobs(f"{analysis_category} jobs", location="Remote")
        live_jobs.extend(fetch_real_jobs(f"{analysis_category} internships", location="Remote"))

        applied_set = set()
        apps = Application.query.filter_by(user_id=current_user.id).all()
        for a in apps:
            applied_set.add((a.job_title.lower().strip(), a.company.lower().strip()))

        for job in live_jobs:
            job_title_lower = (job.get("title") or "").lower().strip()
            job_company_lower = (job.get("company") or "").lower().strip()
            job["has_applied"] = (job_title_lower, job_company_lower) in applied_set

        ranking_source = "live_hybrid"
        ranking_budget_exceeded = False
        job_matches = []

        if live_jobs:
            matcher = _get_job_matcher()
            ranked_live, ranking_budget_exceeded = matcher.rank_live_jobs(
                cleaned_resume=cleaned_text,
                resume_skills=skills_flat,
                live_jobs=live_jobs,
                analysis_categories=[analysis_category],
                skill_weight=cfg.SKILL_WEIGHT,
                time_budget_seconds=cfg.RANKING_TIME_BUDGET_SECONDS,
                description_char_limit=cfg.RANKING_DESC_CHAR_LIMIT,
            )
            if ranking_budget_exceeded:
                ranking_source = "live_api_raw"
                job_matches = ranked_live
            else:
                ranking_source = "live_hybrid"
                job_matches = ranked_live
        # Attempt to fill job_matches with local fallback jobs if needed
        if len(job_matches) < cfg.TOP_N_RECOMMENDATIONS:
            try:
                matcher = _get_job_matcher()
                local_matches = matcher.match(
                    cleaned_resume=cleaned_text,
                    raw_resume=raw_text,
                    predicted_categories=[analysis_category],
                    top_n=cfg.TOP_N_RECOMMENDATIONS,
                    min_score=1.0,  # Lower threshold for local backfill
                )
                
                existing_titles_companies = {
                    (j.get("title", "").lower().strip(), j.get("company", "").lower().strip())
                    for j in job_matches
                }
                
                for job in local_matches:
                    title = (job.get("title") or "").lower().strip()
                    company = (job.get("company") or "").lower().strip()
                    job["has_applied"] = (title, company) in applied_set
                    
                    if (title, company) not in existing_titles_companies:
                        job_matches.append(job)
                        existing_titles_companies.add((title, company))
                        
                        if len(job_matches) >= cfg.TOP_N_RECOMMENDATIONS:
                            break
                            
                if not live_jobs:
                    ranking_source = "local_fallback"
                elif len(job_matches) > len(live_jobs):
                    ranking_source += " + local_fallback"
            except Exception as local_match_err:
                logger.warning(f"Local fallback matcher failed: {local_match_err}")

        # Final score filter & truncation
        if job_matches:
            # Only keep jobs with at least *some* relevance score, but allow leniency to fill the dashboard
            filtered = [j for j in job_matches if j.get("combined_score", 0) >= 2.0]
            if filtered:
                job_matches = filtered
            job_matches = job_matches[:cfg.TOP_N_RECOMMENDATIONS]

        skills_gap = extractor.get_category_gap(analysis_category, skills_flat)

        skill_count = len(skills_flat) if skills_flat else 0
        analyzer = _get_quality_analyzer()
        try:
            quality_report = analyzer.analyze(raw_text, skill_count)
            quality_score = quality_report.get("final_score", 0)
        except Exception as qa_err:
            logger.warning(f"Quality analysis failed: {qa_err}")
            quality_report = {"final_score": 0, "error": str(qa_err)}
            quality_score = 0

        try:
            analysis = ResumeAnalysis(
                user_id=current_user.id,
                filename=file.filename,
                quality_score=quality_score,
                skills_json=json.dumps(skills_flat),
                categories_json=json.dumps(predicted_categories),
            )
            db.session.add(analysis)
            db.session.commit()
        except Exception as e:
            logger.warning(f"Failed to save analysis: {e}")

        response = {
            "success": True,
            "resume_stats": {
                "word_count": len(raw_text.split()),
                "skill_count": skill_count,
                "quality_score": quality_score,
                "quality_report": quality_report,
                "filename": file.filename,
            },
            "skills": {
                "all": skills_flat,
                "grouped": skills_grouped,
            },
            "skills_gap": skills_gap,
            "predicted_categories": predicted_categories,
            "classification_state": classification_state,
            "top_confidence": round(top_confidence, 3),
            "confirmation_choices": confirmation_choices,
            "analysis_category": analysis_category,
            "confirmation_used": confirmation_used,
            "preference_applied": preference_applied,
            "ranking_source": ranking_source,
            "ranking_budget_exceeded": ranking_budget_exceeded,
            "job_recommendations": job_matches,
            "live_jobs": live_jobs,
        }

        logger.info(
            f"Analysis complete: skills={skill_count}, jobs={len(job_matches)}, "
            f"quality={quality_score}%, category={analysis_category}, "
            f"confidence={top_confidence:.3f}, source={ranking_source}, "
            f"budget_exceeded={ranking_budget_exceeded}"
        )
        return jsonify(response)

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@app.route("/api/apply", methods=["POST"])
@login_required
def apply_job():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required."}), 400

    job_title = (data.get("job_title") or "").strip()
    company = (data.get("company") or "").strip()
    job_url = (data.get("job_url") or "").strip()
    job_source = (data.get("job_source") or "curated").strip()

    if not job_title or not company:
        return jsonify({"error": "Job title and company are required."}), 400

    existing = Application.query.filter_by(
        user_id=current_user.id,
        job_title=job_title,
        company=company,
    ).first()

    if existing:
        return jsonify({
            "success": True,
            "message": "You already applied for this role in ResumeAI.",
            "already_applied": True,
            "application": existing.to_dict(),
        })

    application = Application(
        user_id=current_user.id,
        job_title=job_title,
        company=company,
        job_source=job_source,
        job_url=job_url,
    )
    db.session.add(application)
    db.session.commit()

    email_sent = send_application_email(
        to_email=current_user.email,
        user_name=current_user.name,
        job_title=job_title,
        company=company,
    )

    return jsonify({
        "success": True,
        "message": f"Application submitted for {job_title} at {company}!",
        "email_sent": email_sent,
        "application": application.to_dict(),
    })


@app.route("/api/applications")
@login_required
def get_applications():
    apps = Application.query.filter_by(user_id=current_user.id).order_by(Application.applied_at.desc()).all()
    return jsonify({
        "applications": [a.to_dict() for a in apps],
        "total": len(apps),
    })


@app.route("/api/jobs/live")
def live_jobs():
    query = request.args.get("q", "Software Developer")
    location = request.args.get("location", "")
    jobs = fetch_real_jobs(query, location)
    return jsonify({"jobs": jobs, "count": len(jobs)})


@app.route("/api/optimize", methods=["POST"])
@limiter.limit("10 per minute", key_func=_rate_limit_key)
@jwt_required
def optimize_text():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "No text provided to optimize."}), 400

    # Strip scripting exploits or HTML tags from input text
    from engine.security import sanitize_input_text
    data["text"] = sanitize_input_text(data["text"])

    optimizer = _get_ai_optimizer()
    if not optimizer.is_ready:
        return jsonify({
            "error": "AI Optimizer is not ready. Please check if GEMINI_API_KEY is set in .env."
        }), 503

    try:
        optimized = optimizer.refine_bullet(data["text"])
        if not optimized:
            return jsonify({
                "error": "The AI model failed to generate a refinement. This usually means the API is temporarily overloaded or the model name is incorrect."
            }), 502

        return jsonify({
            "success": True,
            "original": data["text"],
            "optimized": optimized,
        })
    except Exception as e:
        logger.error(f"Optimization endpoint error: {e}", exc_info=True)
        return jsonify({"error": f"Internal AI Engine Error: {str(e)}"}), 500


@app.route("/api/optimize/stream", methods=["POST"])
@limiter.limit("10 per minute", key_func=_rate_limit_key)
@jwt_required
def optimize_text_stream():
    from flask import Response, stream_with_context
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "No text provided to optimize."}), 400

    # Strip scripting exploits or HTML tags from input text
    from engine.security import sanitize_input_text
    data["text"] = sanitize_input_text(data["text"])

    optimizer = _get_ai_optimizer()
    if not optimizer.is_ready:
        return jsonify({
            "error": "AI Optimizer is not ready. Please check if GEMINI_API_KEY is set in .env."
        }), 503

    def generate():
        try:
            for chunk in optimizer.refine_bullet_stream(data["text"]):
                yield chunk
        except Exception as e:
            logger.error(f"Error in optimize_text_stream: {e}", exc_info=True)
            yield f"\n[STREAM_ERROR: {str(e)}]"

    return Response(stream_with_context(generate()), mimetype="text/plain")


# ── Employer Blueprint ─────────────────────────────────────────────────────────

from flask import Blueprint, redirect, url_for
from flask_login import login_required

emp_bp = Blueprint("employer", __name__, url_prefix="/employer")


def _emp_required(f):
    """Role guard for employer-only routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login_page"))
        if current_user.role != "employer":
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


@emp_bp.route("/dashboard")
@login_required
def dashboard():
    """Employer dashboard — their job postings with applicant counts."""
    if current_user.role != "employer":
        return redirect(url_for("index"))

    employer = Employer.query.filter_by(user_id=current_user.id).first()
    if not employer:
        return redirect(url_for("index"))

    postings = JobPosting.query.filter_by(employer_id=employer.id).order_by(JobPosting.posted_at.desc()).all()
    posting_summaries = []
    for p in postings:
        app_count = Application.query.filter_by(job_posting_id=p.id).count()
        posting_summaries.append({
            **p.to_dict(),
            "application_count": app_count,
            "company_name": employer.company_name,
            "company_logo": employer.logo_url,
        })

    stages = HiringStage.query.order_by(HiringStage.order).all()
    return render_template(
        "employer_dashboard.html",
        postings=posting_summaries,
        stages=stages,
        employer=employer.to_dict(),
    )


@emp_bp.route("/jobs/new", methods=["GET"])
@login_required
def new_job():
    """Form to create a new job posting."""
    if current_user.role != "employer":
        return redirect(url_for("index"))
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    if not employer:
        return redirect(url_for("index"))
    return render_template("post_job.html", employer=employer.to_dict(), posting=None)


@emp_bp.route("/jobs", methods=["POST"])
@login_required
def create_job():
    """Create a new job posting."""
    if current_user.role != "employer":
        return jsonify({"error": "Forbidden"}), 403

    employer = Employer.query.filter_by(user_id=current_user.id).first()
    if not employer:
        return jsonify({"error": "Employer profile not found."}), 404

    import json as _json
    data = request.get_json() or request.form

    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    if not title or not description:
        return jsonify({"error": "Title and description are required."}), 400

    skills_raw = data.get("skills_required", "")
    if isinstance(skills_raw, str):
        try:
            skills_list = _json.loads(skills_raw) if skills_raw else []
        except Exception:
            skills_list = [s.strip() for s in skills_raw.split(",") if s.strip()]
    else:
        skills_list = skills_raw or []

    posting = JobPosting(
        employer_id=employer.id,
        title=title,
        description=description,
        location=(data.get("location") or "").strip() or None,
        job_type=data.get("job_type", "full-time"),
        experience_level=data.get("experience_level") or None,
        salary_min=int(data.get("salary_min")) if data.get("salary_min") else None,
        salary_max=int(data.get("salary_max")) if data.get("salary_max") else None,
        salary_currency=data.get("salary_currency", "USD"),
        skills_required=_json.dumps(skills_list),
        apply_url=(data.get("apply_url") or "").strip() or None,
    )
    db.session.add(posting)
    db.session.commit()

    return jsonify({"success": True, "posting": posting.to_dict()}), 201


@emp_bp.route("/jobs/<int:job_id>/edit", methods=["GET"])
@login_required
def edit_job(job_id):
    """Edit job form."""
    if current_user.role != "employer":
        return redirect(url_for("index"))
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    if not employer:
        return redirect(url_for("index"))
    posting = JobPosting.query.filter_by(id=job_id, employer_id=employer.id).first_or_404()
    return render_template("post_job.html", employer=employer.to_dict(), posting=posting.to_dict())


@emp_bp.route("/jobs/<int:job_id>", methods=["PUT", "POST"])
@login_required
def update_job(job_id):
    """Update a job posting."""
    if current_user.role != "employer":
        return jsonify({"error": "Forbidden"}), 403

    employer = Employer.query.filter_by(user_id=current_user.id).first()
    if not employer:
        return jsonify({"error": "Employer not found."}), 404

    posting = JobPosting.query.filter_by(id=job_id, employer_id=employer.id).first()
    if not posting:
        return jsonify({"error": "Job not found."}), 404

    import json as _json
    data = request.get_json() or request.form

    posting.title = (data.get("title") or "").strip() or posting.title
    posting.description = (data.get("description") or "").strip() or posting.description
    posting.location = (data.get("location") or "").strip() or posting.location
    posting.job_type = data.get("job_type", posting.job_type)
    posting.experience_level = data.get("experience_level") or posting.experience_level
    posting.salary_min = int(data.get("salary_min")) if data.get("salary_min") else posting.salary_min
    posting.salary_max = int(data.get("salary_max")) if data.get("salary_max") else posting.salary_max
    posting.status = data.get("status", posting.status)

    skills_raw = data.get("skills_required", "")
    if skills_raw:
        try:
            posting.skills_required = _json.dumps(_json.loads(skills_raw))
        except Exception:
            posting.skills_required = _json.dumps([s.strip() for s in str(skills_raw).split(",") if s.strip()])

    posting.apply_url = (data.get("apply_url") or "").strip() or posting.apply_url
    db.session.commit()
    return jsonify({"success": True, "posting": posting.to_dict()})


@emp_bp.route("/jobs/<int:job_id>/close", methods=["POST"])
@login_required
def close_job(job_id):
    """Close a job posting."""
    if current_user.role != "employer":
        return jsonify({"error": "Forbidden"}), 403
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    if not employer:
        return jsonify({"error": "Employer not found."}), 404
    posting = JobPosting.query.filter_by(id=job_id, employer_id=employer.id).first()
    if not posting:
        return jsonify({"error": "Job not found."}), 404
    posting.status = "closed"
    db.session.commit()
    return jsonify({"success": True})


@emp_bp.route("/jobs/<int:job_id>/applicants")
@login_required
def job_applicants(job_id):
    """ATS pipeline view for a specific job."""
    if current_user.role != "employer":
        return redirect(url_for("index"))
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    if not employer:
        return redirect(url_for("index"))
    posting = JobPosting.query.filter_by(id=job_id, employer_id=employer.id).first_or_404()

    applications = Application.query.filter_by(job_posting_id=job_id).all()
    stages = HiringStage.query.order_by(HiringStage.order).all()

    # Build pipeline: { stage_id: [applications] }
    pipeline = {s.id: [] for s in stages}
    unassigned = []
    for app in applications:
        if app.stage_id and app.stage_id in pipeline:
            pipeline[app.stage_id].append({
                **app.to_dict(),
                "candidate_name": app.user.name,
                "candidate_email": app.user.email,
                "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            })
        else:
            unassigned.append({
                **app.to_dict(),
                "candidate_name": app.user.name,
                "candidate_email": app.user.email,
                "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            })

    # Get resume analysis for each candidate
    analyses = {a.user_id: a for a in ResumeAnalysis.query.filter(
        ResumeAnalysis.user_id.in_([app.user_id for app in applications])
    ).all()}

    return render_template(
        "applicants.html",
        posting=posting.to_dict(),
        stages=stages,
        pipeline=pipeline,
        unassigned=unassigned,
        analyses=analyses,
        employer=employer.to_dict(),
    )


@emp_bp.route("/application/<int:app_id>/stage", methods=["POST"])
@login_required
def update_application_stage(app_id):
    """Move an application to a new stage."""
    if current_user.role != "employer":
        return jsonify({"error": "Forbidden"}), 403
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    if not employer:
        return jsonify({"error": "Employer not found."}), 404

    app = Application.query.get(app_id)
    if not app or not app.job_posting_id:
        return jsonify({"error": "Application not found."}), 404
    posting = JobPosting.query.filter_by(id=app.job_posting_id, employer_id=employer.id).first()
    if not posting:
        return jsonify({"error": "Not authorized."}), 403

    data = request.get_json() or {}
    new_stage_id = data.get("stage_id")
    notes = (data.get("notes") or "").strip()

    if not new_stage_id:
        return jsonify({"error": "stage_id is required."}), 400

    stage = HiringStage.query.get(new_stage_id)
    if not stage:
        return jsonify({"error": "Invalid stage."}), 400

    # Log status change
    status_log = ApplicationStatus(application_id=app.id, stage_id=new_stage_id, notes=notes)
    db.session.add(status_log)
    app.stage_id = new_stage_id
    db.session.commit()
    return jsonify({"success": True, "application": app.to_dict()})


@emp_bp.route("/application/<int:app_id>/detail")
@login_required
def application_detail(app_id):
    """View a single applicant's details."""
    if current_user.role != "employer":
        return redirect(url_for("index"))
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    if not employer:
        return redirect(url_for("index"))

    app = Application.query.get(app_id)
    if not app:
        return redirect(url_for("index"))
    if app.job_posting_id:
        posting = JobPosting.query.filter_by(id=app.job_posting_id, employer_id=employer.id).first()
        if not posting:
            return redirect(url_for("index"))

    stages = HiringStage.query.order_by(HiringStage.order).all()
    status_history = ApplicationStatus.query.filter_by(application_id=app.id).order_by(ApplicationStatus.changed_at).all()
    analysis = ResumeAnalysis.query.filter_by(user_id=app.user_id).order_by(ResumeAnalysis.analyzed_at.desc()).first()

    return render_template(
        "candidate_detail.html",
        application=app.to_dict(),
        candidate=app.user.to_dict(),
        stages=stages,
        status_history=[s.to_dict() for s in status_history],
        analysis=analysis,
        employer=employer.to_dict(),
    )


@emp_bp.route("/candidates/search")
@login_required
def search_candidates():
    """Search candidates by skill or category."""
    if current_user.role != "employer":
        return jsonify({"error": "Forbidden"}), 403

    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"candidates": []})

    # Search by skills in resume analysis
    analyses = ResumeAnalysis.query.all()
    matched = []
    q_lower = q.lower()
    for a in analyses:
        if not a.skills_json:
            continue
        skills = json.loads(a.skills_json)
        if any(q_lower in s.lower() for s in skills):
            matched.append({
                "user_id": a.user_id,
                "name": a.user.name,
                "email": a.user.email,
                "filename": a.filename,
                "quality_score": a.quality_score,
                "skills": skills,
            })
        if len(matched) >= 20:
            break

    return jsonify({"candidates": matched})


app.register_blueprint(emp_bp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
