"""
System Health Checker for ResumeAI
Verifies all core services and configurations without starting the full app.
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Set up logging to console only for this script
logger = logging.getLogger("system_check")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def check_env():
    logger.info("Checking environment variables...")
    load_dotenv()
    required = ["SECRET_KEY", "GEMINI_API_KEY", "JSEARCH_API_KEY"]
    missing = [var for var in required if not os.environ.get(var)]
    
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        return False
    logger.info("✓ Environment variables OK.")
    return True

def check_proxy_bypass():
    logger.info("Checking proxy bypass integration...")
    from engine.network_utils import bypass_proxies, get_robust_session
    bypass_proxies()
    
    # Verify sensitive vars are cleared if they were set
    for var in ["HTTP_PROXY", "HTTPS_PROXY"]:
        if var in os.environ:
             logger.error(f"Failed to clear {var}")
             return False
    logger.info("✓ Proxy bypass OK.")
    return True

def check_db():
    logger.info("Checking database connection...")
    try:
        from app import app, db
        with app.app_context():
            db.engine.connect()
            from models import User
            count = User.query.count()
            logger.info(f"✓ Database connection OK. Found {count} users.")
        return True
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return False

def check_gemini():
    logger.info("Checking Gemini AI connectivity...")
    try:
        from engine.ai_optimizer import AIOptimizer
        api_key = os.environ.get("GEMINI_API_KEY")
        model_name = os.environ.get("GEMINI_MODEL_NAME", "gemini-2.5-flash")
        optimizer = AIOptimizer(api_key, model_name)
        
        if optimizer.is_ready:
            logger.info(f"✓ Gemini AI Initialized with model: {model_name}")
            return True
        else:
            logger.error("Gemini AI failed to initialize.")
            return False
    except Exception as e:
        logger.error(f"Gemini connectivity check failed: {e}")
        return False

def check_jsearch():
    logger.info("Checking JSearch API connectivity...")
    try:
        from engine.job_api import fetch_real_jobs
        # Non-destructive fetch (just a small query)
        jobs = fetch_real_jobs("Software Developer", location="Remote", page=1)
        if jobs:
            logger.info(f"✓ JSearch API OK. Fetched {len(jobs)} jobs.")
        else:
            logger.warning("JSearch API returned no results (might be rate limited or key issue).")
        return True # Not failing just for 0 results
    except Exception as e:
        logger.error(f"JSearch API check failed: {e}")
        return False

def run_all():
    print("\n" + "="*40)
    print("      RESUME AI SYSTEM HEALTH CHECK")
    print("="*40)
    
    steps = [
        ("Environment", check_env),
        ("Proxy Bypass", check_proxy_bypass),
        ("Database", check_db),
        ("Gemini AI", check_gemini),
        ("JSearch API", check_jsearch)
    ]
    
    results = []
    for name, func in steps:
        try:
            success = func()
            results.append((name, success))
        except Exception as e:
            logger.error(f"Unexpected error in {name} check: {e}")
            results.append((name, False))
            
    print("\n" + "="*40)
    print("               SUMMARY")
    print("="*40)
    all_ok = True
    for name, success in results:
        status = "PASSED" if success else "FAILED"
        print(f"{name:<15}: {status}")
        if not success: all_ok = False
        
    print("="*40)
    if all_ok:
        print("[SUCCESS] ALL SYSTEMS OPERATIONAL")
    else:
        print("[FAILED] SYSTEM ERRORS DETECTED")
    print("="*40 + "\n")
    return all_ok

if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
