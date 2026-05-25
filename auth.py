"""Authentication blueprint for Resume Analyzer."""
import os
import re
import random

import requests
from flask import Blueprint, request, jsonify, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from config import get_config
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
try:
    from twilio.rest import Client as TwilioClient
except ImportError:
    TwilioClient = None

cfg = get_config()
if TwilioClient and cfg.TWILIO_ACCOUNT_SID:
    twilio_client = TwilioClient(cfg.TWILIO_ACCOUNT_SID, cfg.TWILIO_AUTH_TOKEN)
else:
    twilio_client = None

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

from engine.network_utils import get_robust_session
from functools import wraps

def _google_request():
    """Create a request transport that does not inherit broken local proxy settings."""
    session = get_robust_session()
    session.headers.update({"Connection": "close"})
    return google_requests.Request(session=session)


def _validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


@auth_bp.route("/signup", methods=["POST"])
def signup():
    """Create a new user account."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required."}), 400

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    # Validation
    if not name or len(name) < 2:
        return jsonify({"error": "Name must be at least 2 characters."}), 400
    if not _validate_email(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    # Check if email already exists
    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "An account with this email already exists."}), 409

    # Create user
    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    # Auto-login after signup
    login_user(user, remember=True)

    return jsonify({
        "success": True,
        "message": "Account created successfully!",
        "user": user.to_dict(),
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """Log in an existing user."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required."}), 400

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password."}), 401

    login_user(user, remember=True)

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user.name}!",
        "user": user.to_dict(),
    })


@auth_bp.route("/logout")
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    return jsonify({"success": True, "message": "Logged out successfully."})


@auth_bp.route("/me")
def me():
    """Get current user info (or null if not authenticated)."""
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "user": current_user.to_dict(),
        })
    return jsonify({"authenticated": False, "user": None})


# ── Google OAuth ─────────────────────────────────────────────────────────────

@auth_bp.route("/google/verify", methods=["POST"])
def google_verify():
    """Verify Google token sent from frontend."""
    data = request.get_json()
    token = data.get("credential")
    if not token:
        return jsonify({"error": "No token provided."}), 400

    try:
        idinfo = id_token.verify_oauth2_token(
            token, _google_request(), cfg.GOOGLE_CLIENT_ID
        )
        # ID token is valid.
        google_id = idinfo["sub"]
        email_raw = idinfo.get("email")
        email = email_raw.lower().strip() if email_raw else None
        name = idinfo.get("name") or (email.split("@")[0] if email else "Google User")
        
        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            # Check if email is already in use by a standard account
            user = User.query.filter_by(email=email).first()
            if user:
                # Link account
                user.google_id = google_id
            else:
                # Create new user
                user = User(name=name, email=email, google_id=google_id, password_hash="")
                db.session.add(user)
            try:
                db.session.commit()
            except Exception as dbe:
                db.session.rollback()
                print(f"DB Error: {dbe}")
                return jsonify({"error": f"DB Error: {str(dbe)}"}), 500
            
        login_user(user, remember=True)
        return jsonify({"success": True, "message": f"Welcome, {name}!"})
        
    except ValueError as e:
        print(f"Google Token Validation Error: {e}")
        return jsonify({"error": "Invalid token."}), 401
    except Exception as e:
        print(f"Google Auth Internal Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Authentication internal error: {str(e)}"}), 500


# ── Mobile OTP (Developer Mode) ──────────────────────────────────────────────

# Temporary in-memory store for OTPs (For production use Redis)
_otp_store = {}

@auth_bp.route("/otp/send", methods=["POST"])
def otp_send():
    """Send an OTP (Printed to console in Dev Mode)."""
    data = request.get_json()
    phone = (data.get("phone") or "").strip()
    if not phone or len(phone) < 7:
        return jsonify({"error": "Invalid phone number."}), 400

    # Normalize phone: ensure starts with + (Twilio requirement)
    if not phone.startswith("+"):
        if len(phone) == 10: # Assume US/India regional
             # This is a guestimate; in production we should use phonenumbers lib
             # For now, just add a + if it looks like it's missing the prefix
             # or just warn the user. Let's try adding '+' as a basic fix.
             pass 

    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    _otp_store[phone] = otp
    
    # Send SMS via Twilio
    if twilio_client:
        try:
            # Twilio requires E.164. If user didn't provide +, we might need to add it
            # But we don't know the country. Let's at least log what we are sending.
            target_phone = phone if phone.startswith("+") else f"+{phone}"
            print(f"Attempting to send OTP to {target_phone} via Twilio...")
            
            message = twilio_client.messages.create(
                body=f"Your ResumeAI Login Code is: {otp}. Do not share this code.",
                from_=cfg.TWILIO_PHONE_NUMBER,
                to=target_phone
            )
            print(f"Twilio SMS Sent: {message.sid}")
        except Exception as e:
            print(f"Twilio API Error: {e}")
            return jsonify({"error": f"SMS Service Error: {str(e)}"}), 500
    else:
        # Fallback to Developer Mode if Twilio failed to load
        print(f"\n" + "="*40)
        print(f"🔒 OTP REQUESTED FOR: {phone}")
        print(f"🔑 YOUR ONE-TIME PASSWORD IS: {otp}")
        print("="*40 + "\n")
    
    return jsonify({"success": True, "message": "OTP sent safely."})

@auth_bp.route("/otp/verify", methods=["POST"])
def otp_verify():
    """Verify the submitted OTP."""
    data = request.get_json()
    phone = (data.get("phone") or "").strip()
    otp = (data.get("otp") or "").strip()
    name = (data.get("name") or "").strip() # Optional, sent on signup
    
    if not phone or not otp:
        return jsonify({"error": "Phone and OTP required."}), 400
        
    expected_otp = _otp_store.get(phone)
    if expected_otp != otp:
        return jsonify({"error": "Invalid or expired OTP."}), 401
        
    # Clear OTP
    del _otp_store[phone]
    
    # Login or Register
    user = User.query.filter_by(phone_number=phone).first()
    if not user:
        if not name:
            name = "Mobile User" # Default fallback
        user = User(name=name, phone_number=phone)
        db.session.add(user)
        db.session.commit()
        
    login_user(user, remember=True)
    return jsonify({"success": True, "message": f"Welcome back, {user.name}!"})


# ── Employer Auth ──────────────────────────────────────────────────────────────

def role_required(role):
    """Decorator to restrict routes to users with a specific role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Please log in first.", "auth_required": True}), 401
            if current_user.role != role:
                return jsonify({"error": f"Access denied. This page is for {role}s only."}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@auth_bp.route("/employer/register", methods=["POST"])
def employer_register():
    """Register a new employer account."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required."}), 400

    company_name = (data.get("company_name") or "").strip()
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not company_name or len(company_name) < 2:
        return jsonify({"error": "Company name must be at least 2 characters."}), 400
    if not name or len(name) < 2:
        return jsonify({"error": "Contact name must be at least 2 characters."}), 400
    if not _validate_email(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "An account with this email already exists."}), 409

    # Create user as employer
    user = User(name=name, email=email, role="employer")
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # get user.id

    # Create employer profile
    from models import Employer
    employer = Employer(
        user_id=user.id,
        company_name=company_name,
        website=data.get("website", "").strip() or None,
        company_size=data.get("company_size", "").strip() or None,
        industry=data.get("industry", "").strip() or None,
    )
    db.session.add(employer)
    db.session.commit()

    login_user(user, remember=True)
    return jsonify({
        "success": True,
        "message": "Employer account created successfully!",
        "user": user.to_dict(),
    }), 201


@auth_bp.route("/employer/login", methods=["POST"])
def employer_login():
    """Log in an employer account."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required."}), 400

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password."}), 401
    if user.role != "employer":
        return jsonify({"error": "This account is not registered as an employer."}), 403

    login_user(user, remember=True)
    return jsonify({
        "success": True,
        "message": f"Welcome back, {user.name}!",
        "user": user.to_dict(),
    })
