"""Network utilities to handle proxy-related issues and robust sessions."""
import os
import requests
import logging

logger = logging.getLogger(__name__)

def bypass_proxies():
    """
    Forcefully clear proxy environment variables from the current process.
    This fixes issues where libraries like requests/urllib3 pick up broken 
    system-level proxies (e.g., 127.0.0.1:9) even when trust_env is False.
    """
    proxy_vars = [
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", 
        "http_proxy", "https_proxy", "all_proxy",
        "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"
    ]
    
    cleared = []
    for var in proxy_vars:
        if var in os.environ:
            del os.environ[var]
            cleared.append(var)
    
    if cleared:
        logger.info(f"Bypassed system proxies by clearing: {', '.join(cleared)}")

    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"
    
def get_robust_session():
    """Returns a requests session with proxies explicitly disabled."""
    session = requests.Session()
    session.trust_env = False
    session.proxies = {
        "http": None,
        "https": None,
    }
    return session
