"""Email notification service for Resume Analyzer."""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def _get_mail_config():
    return {
        "username": os.environ.get("MAIL_USERNAME", ""),
        "password": os.environ.get("MAIL_PASSWORD", ""),
        "from_name": os.environ.get("MAIL_FROM_NAME", "ResumeAI"),
    }


def send_application_email(to_email, user_name, job_title, company):
    """
    Send a 'Thanks for applying' confirmation email.

    Returns True if sent successfully, False otherwise.
    """
    config = _get_mail_config()
    if not config["username"] or not config["password"]:
        logger.debug("Email not configured, skipping confirmation email.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Application Confirmed — {job_title} at {company}"
        msg["From"] = f"{config['from_name']} <{config['username']}>"
        msg["To"] = to_email

        # Plain text fallback
        text_body = f"""
Hi {user_name},

Your application has been submitted successfully!

Position: {job_title}
Company: {company}

We wish you the best of luck with your application!

Best regards,
ResumeAI Team
        """.strip()

        # Styled HTML email
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 0; background: #f5f7fb; }}
        .container {{ max-width: 560px; margin: 40px auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }}
        .header {{ background: linear-gradient(135deg, #667eea, #764ba2); padding: 32px; text-align: center; }}
        .header h1 {{ color: white; margin: 0; font-size: 24px; }}
        .header p {{ color: rgba(255,255,255,0.8); margin: 8px 0 0; font-size: 14px; }}
        .body {{ padding: 32px; }}
        .greeting {{ font-size: 18px; font-weight: 600; color: #1a1a2e; margin-bottom: 16px; }}
        .message {{ color: #4a4a6a; line-height: 1.7; margin-bottom: 24px; }}
        .job-card {{ background: #f8f9fc; border: 1px solid #e8e9f0; border-radius: 12px; padding: 20px; margin-bottom: 24px; }}
        .job-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: #7a7a96; margin-bottom: 4px; }}
        .job-value {{ font-size: 16px; font-weight: 600; color: #1a1a2e; margin-bottom: 12px; }}
        .success-badge {{ display: inline-block; background: rgba(52, 211, 153, 0.12); color: #059669; padding: 6px 16px; border-radius: 20px; font-size: 13px; font-weight: 600; }}
        .footer {{ padding: 24px 32px; text-align: center; border-top: 1px solid #f0f0f5; }}
        .footer p {{ color: #7a7a96; font-size: 12px; margin: 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Application Confirmed ✓</h1>
            <p>ResumeAI Job Application System</p>
        </div>
        <div class="body">
            <div class="greeting">Hi {user_name}! 👋</div>
            <div class="message">
                Great news! Your application has been submitted successfully through ResumeAI.
                Here are the details:
            </div>
            <div class="job-card">
                <div class="job-label">Position</div>
                <div class="job-value">{job_title}</div>
                <div class="job-label">Company</div>
                <div class="job-value">{company}</div>
                <div class="job-label">Status</div>
                <div><span class="success-badge">✓ Application Submitted</span></div>
            </div>
            <div class="message">
                We wish you the best of luck! Keep using ResumeAI to discover more
                opportunities that match your skills.
            </div>
        </div>
        <div class="footer">
            <p>This email was sent by ResumeAI — AI-powered resume analysis &amp; job matching.</p>
            <p>Your resume data is processed in-memory and never stored.</p>
        </div>
    </div>
</body>
</html>
        """.strip()

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=5.0) as smtp:
            smtp.login(config["username"], config["password"])
            smtp.send_message(msg)

        logger.info(f"Confirmation email sent to {to_email} for {job_title} at {company}")
        return True

    except Exception as e:
        logger.warning(f"Failed to send email to {to_email}: {e}")
        return False


def send_welcome_email(to_email, user_name):
    """
    Send a beautifully styled dark-mode welcome email to a newly registered user.

    Returns True if sent successfully, False otherwise.
    """
    config = _get_mail_config()
    if not config["username"] or not config["password"]:
        logger.debug("Email not configured, skipping welcome email.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Welcome to ResumeAI! 🚀 Let's supercharge your career"
        msg["From"] = f"{config['from_name']} <{config['username']}>"
        msg["To"] = to_email

        # Plain text fallback
        text_body = f"""
Hi {user_name},

Thank you for registering at ResumeAI! We're thrilled to help you analyze, optimize, and match your profile with your dream career opportunities.

Here is what you can do with your new account right now:

1. AI Resume Analysis
Get a deep quality score, career category prediction, and custom recommendations.

2. AI Optimization Lab
Refine weak bullet points into metrics-driven, high-impact achievements powered by Gemini AI.

3. Personalized Job Matches
Browse active, remote jobs and internships ranked by compatibility with your resume.

Get started by uploading your resume today: https://resume-ai-8xd3.onrender.com

Best regards,
The ResumeAI Team
https://resume-ai-8xd3.onrender.com
        """.strip()

        # Premium styled HTML template
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #0b0f19;
            color: #f3f4f6;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background-color: #0b0f19;
            border: 1px solid #1e293b;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            padding: 32px;
        }}
        .logo-header {{
            text-align: center;
            margin-bottom: 24px;
        }}
        .logo-text {{
            font-size: 24px;
            font-weight: 800;
            color: #ffffff;
        }}
        .logo-accent {{
            color: #6366f1;
        }}
        .logo-subtext {{
            font-size: 11px;
            color: #a855f7;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
            margin-top: 4px;
        }}
        hr {{
            border: 0;
            border-top: 1px solid #1e293b;
            margin-bottom: 24px;
        }}
        .greeting {{
            font-size: 16px;
            line-height: 1.6;
            color: #f3f4f6;
            margin-bottom: 12px;
        }}
        .intro-text {{
            font-size: 15px;
            line-height: 1.6;
            color: #94a3b8;
            margin-bottom: 24px;
        }}
        .sub-greeting {{
            font-size: 15px;
            line-height: 1.6;
            color: #f3f4f6;
            font-weight: 600;
            margin-top: 24px;
            margin-bottom: 16px;
        }}
        .feature-title {{
            color: #ffffff;
            font-size: 14px;
            font-weight: 700;
            display: block;
            margin-bottom: 2px;
        }}
        .feature-desc {{
            font-size: 13px;
            color: #94a3b8;
            line-height: 1.5;
        }}
        .cta-container {{
            text-align: center;
            margin: 32px 0 24px 0;
        }}
        .cta-btn {{
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
            color: #ffffff !important;
            text-decoration: none;
            padding: 12px 30px;
            font-weight: 700;
            border-radius: 50px;
            font-size: 14px;
            display: inline-block;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
        }}
        .signature-text {{
            font-size: 13px;
            color: #94a3b8;
            line-height: 1.6;
            margin-bottom: 0;
        }}
        .signature-brand {{
            color: #ffffff;
            font-weight: 700;
        }}
        .link {{
            color: #6366f1;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo-header">
            <span class="logo-text">Resume<span class="logo-accent">AI</span></span>
            <div class="logo-subtext">AI-Powered Career Intelligence</div>
        </div>
        <hr>
        <div class="greeting">Hi <strong>{user_name}</strong>,</div>
        <div class="intro-text">
            Thank you for registering at <strong>ResumeAI</strong>! We're thrilled to help you analyze, optimize, and match your profile with your dream career opportunities.
        </div>
        <div class="sub-greeting">Here is what you can do with your new account right now:</div>
        
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 24px;">
            <tr>
                <td valign="top" width="32" style="font-size: 20px; padding-top: 2px;">🔍</td>
                <td>
                    <strong class="feature-title">AI Resume Analysis</strong>
                    <span class="feature-desc">Get a deep quality score, career category prediction, and custom recommendations.</span>
                </td>
            </tr>
            <tr style="height: 16px;"><td colspan="2"></td></tr>
            <tr>
                <td valign="top" width="32" style="font-size: 20px; padding-top: 2px;">🤖</td>
                <td>
                    <strong class="feature-title">AI Optimization Lab</strong>
                    <span class="feature-desc">Refine weak bullet points into metrics-driven, high-impact achievements powered by Gemini AI.</span>
                </td>
            </tr>
            <tr style="height: 16px;"><td colspan="2"></td></tr>
            <tr>
                <td valign="top" width="32" style="font-size: 20px; padding-top: 2px;">💼</td>
                <td>
                    <strong class="feature-title">Personalized Job Matches</strong>
                    <span class="feature-desc">Browse active, remote jobs and internships ranked by compatibility with your resume.</span>
                </td>
            </tr>
        </table>

        <div class="cta-container">
            <a href="https://resume-ai-8xd3.onrender.com" class="cta-btn">Analyze Your Resume Now &rarr;</a>
        </div>
        <hr>
        <p class="signature-text">
            Best regards,<br>
            <strong class="signature-brand">The ResumeAI Team</strong><br>
            <a href="https://resume-ai-8xd3.onrender.com" class="link">resume-ai-8xd3.onrender.com</a>
        </p>
    </div>
</body>
</html>
        """.strip()

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=5.0) as smtp:
            smtp.login(config["username"], config["password"])
            smtp.send_message(msg)

        logger.info(f"Welcome email successfully sent to {to_email}")
        return True

    except Exception as e:
        logger.warning(f"Failed to send welcome email to {to_email}: {e}")
        return False
