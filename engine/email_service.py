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

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(config["username"], config["password"])
            smtp.send_message(msg)

        logger.info(f"Confirmation email sent to {to_email} for {job_title} at {company}")
        return True

    except Exception as e:
        logger.warning(f"Failed to send email to {to_email}: {e}")
        return False
