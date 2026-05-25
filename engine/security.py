"""Security Engine — cryptographic JWT handling and robust text input sanitization."""
import re
import hmac
import json
import time
import base64
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def base64url_encode(data: bytes) -> str:
    """Helper to base64url-encode bytes."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def base64url_decode(data: str) -> bytes:
    """Helper to decode base64url string back to bytes."""
    padding = '=' * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def generate_jwt_token(user_id: int, secret_key: str, expires_in: int = 3600) -> str:
    """
    Generates a secure, signed JSON Web Token (JWT) using standard HMAC-SHA256 signature algorithm.
    Does not require external dependencies like PyJWT.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "user_id": user_id,
        "exp": int(time.time()) + expires_in,
        "iat": int(time.time())
    }

    header_b64 = base64url_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = base64url_encode(json.dumps(payload).encode('utf-8'))

    # Construct signature input
    sig_input = f"{header_b64}.{payload_b64}".encode('utf-8')

    # Calculate HMAC-SHA256 signature using secret key
    signature = hmac.new(secret_key.encode('utf-8'), sig_input, 'sha256').digest()
    sig_b64 = base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_jwt_token(token: str, secret_key: str) -> Optional[dict]:
    """
    Decodes and validates a JSON Web Token.
    Returns the parsed payload if the signature is valid and token is not expired, else returns None.
    """
    if not token or not isinstance(token, str):
        return None

    parts = token.strip().split('.')
    if len(parts) != 3:
        logger.warning("Invalid JWT structure: must consist of 3 parts separated by dots")
        return None

    header_b64, payload_b64, sig_b64 = parts

    try:
        # 1. Verify HMAC-SHA256 Signature
        sig_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_signature = hmac.new(secret_key.encode('utf-8'), sig_input, 'sha256').digest()
        expected_sig_b64 = base64url_encode(expected_signature)

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(sig_b64.encode('utf-8'), expected_sig_b64.encode('utf-8')):
            logger.warning("JWT validation failed: signature mismatch")
            return None

        # 2. Decode and parse Payload
        payload_bytes = base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode('utf-8'))

        # 3. Check Expiry
        exp = payload.get("exp")
        if exp and exp < time.time():
            logger.warning("JWT validation failed: token has expired")
            return None

        return payload
    except Exception as e:
        logger.error(f"Failed to decode or validate JWT token: {e}")
        return None


def sanitize_input_text(text: str) -> str:
    """
    Cleans and strips malicious payloads, scripting injections, HTML blocks,
    executable scripts, and LLM prompt hijack attempts (including backticks and escape signals).
    """
    if not text or not isinstance(text, str):
        return ""

    # 1. Strip script tags and everything inside them recursively
    sanitized = re.sub(
        r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
        "",
        text,
        flags=re.IGNORECASE
    )

    # 2. Remove standard HTML/XML tags
    sanitized = re.sub(r"<[^>]+>", "", sanitized)

    # 3. Strip standard script event handlers and executable vectors
    exploit_vectors = [
        r"javascript:",
        r"onerror=",
        r"onload=",
        r"onclick=",
        r"onmouseover=",
        r"onfocus=",
        r"onblur=",
        r"alert\(",
        r"eval\(",
        r"document\.cookie",
        r"window\.location",
        r"exec\("
    ]
    for vector in exploit_vectors:
        sanitized = re.sub(vector, "", sanitized, flags=re.IGNORECASE)

    # 4. Prompt Injection Mitigations:
    # Strip backticks completely (both triple and single) to prevent prompt boundary escaping
    sanitized = sanitized.replace("```", "").replace("`", "")

    # Strip system override phrases often used in jailbreak payloads
    jailbreak_phrases = [
        r"ignore (?:all )?previous instructions",
        r"system override",
        r"you are now a",
        r"forget your (?:original )?directives",
        r"bypass safety settings",
        r"bypass rules"
    ]
    for phrase in jailbreak_phrases:
        sanitized = re.sub(phrase, "", sanitized, flags=re.IGNORECASE)

    return sanitized.strip()
