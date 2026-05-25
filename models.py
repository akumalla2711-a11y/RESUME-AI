"""Database models for Resume Analyzer."""
import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model, UserMixin):
    """User account model — both candidates and employers share this table."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(256), nullable=True)
    phone_number = db.Column(db.String(30), unique=True, nullable=True, index=True)
    google_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    role = db.Column(db.String(20), nullable=False, default="candidate")  # 'candidate' or 'employer'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    analyses = db.relationship("ResumeAnalysis", backref="user", lazy=True)
    applications = db.relationship("Application", backref="user", lazy=True)
    preference = db.relationship("UserPreference", backref="user", lazy=True, uselist=False)
    category_feedback = db.relationship("CategoryFeedback", backref="user", lazy=True)
    employer_profile = db.relationship("Employer", backref="user", uselist=False)
    saved_jobs = db.relationship("SavedJob", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "preferred_category": self.preference.preferred_category if self.preference else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserPreference(db.Model):
    """Persistent user-level category preference (soft hint, not hard lock)."""
    __tablename__ = "user_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True, index=True)
    preferred_category = db.Column(db.String(120), nullable=False, index=True)
    source = db.Column(db.String(50), default="user_confirmation")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "preferred_category": self.preferred_category,
            "source": self.source,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CategoryFeedback(db.Model):
    """Stores explicit model corrections to build a golden dataset."""
    __tablename__ = "category_feedback"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    predicted_category = db.Column(db.String(120), nullable=False)
    predicted_confidence = db.Column(db.Float, nullable=False, default=0.0)
    confirmed_category = db.Column(db.String(120), nullable=False, index=True)
    cleaned_resume_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "predicted_category": self.predicted_category,
            "predicted_confidence": self.predicted_confidence,
            "confirmed_category": self.confirmed_category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ResumeAnalysis(db.Model):
    """Saved resume analysis results."""
    __tablename__ = "resume_analyses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    filename = db.Column(db.String(255))
    quality_score = db.Column(db.Integer)
    skills_json = db.Column(db.Text)       # JSON string
    categories_json = db.Column(db.Text)   # JSON string
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)


class Application(db.Model):
    """Job application tracking — now links to a real JobPosting."""
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    job_posting_id = db.Column(db.Integer, db.ForeignKey("job_postings.id"), nullable=True)  # null for JSearch/external jobs
    # Legacy fields kept for external job applications (JSearch etc.)
    job_title = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255), nullable=False)
    job_source = db.Column(db.String(50), default="curated")  # 'curated', 'jsearch', or 'employer_posted'
    job_url = db.Column(db.String(512))
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default="applied")

    # Current hiring stage (FK to hiring_stages)
    stage_id = db.Column(db.Integer, db.ForeignKey("hiring_stages.id"), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "job_posting_id": self.job_posting_id,
            "job_title": self.job_title,
            "company": self.company,
            "job_source": self.job_source,
            "job_url": self.job_url,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "status": self.status,
            "stage_id": self.stage_id,
        }


class Employer(db.Model):
    """Employer/company profile — linked to a User with role='employer'."""
    __tablename__ = "employers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True, index=True)
    company_name = db.Column(db.String(255), nullable=False)
    company_description = db.Column(db.Text, nullable=True)
    website = db.Column(db.String(512), nullable=True)
    logo_url = db.Column(db.String(512), nullable=True)
    company_size = db.Column(db.String(50), nullable=True)  # e.g. "1-10", "51-200", "500+"
    industry = db.Column(db.String(120), nullable=True)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    job_postings = db.relationship("JobPosting", backref="employer", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company_name": self.company_name,
            "company_description": self.company_description,
            "website": self.website,
            "logo_url": self.logo_url,
            "company_size": self.company_size,
            "industry": self.industry,
            "verified": self.verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class JobPosting(db.Model):
    """A job posting created by an employer."""
    __tablename__ = "job_postings"

    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("employers.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(255), nullable=True)
    job_type = db.Column(db.String(50), default="full-time")  # full-time, part-time, internship, contract
    experience_level = db.Column(db.String(50), nullable=True)  # entry, mid, senior
    salary_min = db.Column(db.Integer, nullable=True)
    salary_max = db.Column(db.Integer, nullable=True)
    salary_currency = db.Column(db.String(10), default="USD")
    skills_required = db.Column(db.Text, nullable=True)  # JSON string of list
    apply_url = db.Column(db.String(512), nullable=True)  # external apply link, or null for platform apply
    status = db.Column(db.String(20), default="open")  # open, closed, draft
    posted_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    applications = db.relationship("Application", backref="job_posting", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "employer_id": self.employer_id,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "job_type": self.job_type,
            "experience_level": self.experience_level,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_currency": self.salary_currency,
            "skills_required": json.loads(self.skills_required) if self.skills_required else [],
            "apply_url": self.apply_url,
            "status": self.status,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class SavedJob(db.Model):
    """A candidate bookmarking a job without applying."""
    __tablename__ = "saved_jobs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    job_posting_id = db.Column(db.Integer, db.ForeignKey("job_postings.id"), nullable=False, index=True)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "job_posting_id", name="uq_saved_job"),
    )


class HiringStage(db.Model):
    """A hiring pipeline stage (e.g. Applied, Screening, Interview, Offer, Hired, Rejected)."""
    __tablename__ = "hiring_stages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    order = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(20), default="#6c757d")  # hex color for UI
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "order": self.order,
            "color": self.color,
        }


class ApplicationStatus(db.Model):
    """Audit log — each time an application's stage changes, it's recorded here."""
    __tablename__ = "application_statuses"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True)
    stage_id = db.Column(db.Integer, db.ForeignKey("hiring_stages.id"), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    stage = db.relationship("HiringStage")

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "stage_id": self.stage_id,
            "stage_name": self.stage.name if self.stage else None,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "notes": self.notes,
        }
