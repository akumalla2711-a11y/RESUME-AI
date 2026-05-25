"""Real job search integration via JSearch API (RapidAPI)."""
import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

# In-memory cache: { "query_key": { "data": [...], "timestamp": float } }
_cache = {}
CACHE_TTL = 3600  # Cache results for 1 hour


from engine.network_utils import get_robust_session

def _build_session():
    """Create a requests session that ignores broken machine-level proxy settings."""
    return get_robust_session()


def _get_api_key():
    return os.environ.get("JSEARCH_API_KEY", "")


def fetch_real_jobs(query, location="", page=1, num_pages=1):
    """
    Fetch real job listings from JSearch API.

    Args:
        query: Job search query (e.g., "Python Developer")
        location: Location filter (e.g., "Remote", "New York")
        page: Page number
        num_pages: Number of pages to fetch

    Returns:
        List of normalized job dicts, or empty list on failure
    """
    api_key = _get_api_key()
    if not api_key:
        logger.debug("JSearch API key not configured, skipping live jobs.")
        return []

    # Check cache
    cache_key = f"{query}|{location}|{page}"
    cached = _cache.get(cache_key)
    if cached and (time.time() - cached["timestamp"]) < CACHE_TTL:
        logger.debug(f"Returning cached results for: {query}")
        return cached["data"]

    url = "https://jsearch.p.rapidapi.com/search"
    params = {
        "query": f"{query} {location}".strip(),
        "page": str(page),
        "num_pages": str(num_pages),
    }
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "jsearch.p.rapidapi.com",
    }

    try:
        response = _build_session().get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        raw_jobs = data.get("data", [])

        # Normalize to our format
        jobs = []
        for job in raw_jobs:
            normalized = _normalize_job(job)
            if normalized:
                jobs.append(normalized)

        # Cache the results
        _cache[cache_key] = {"data": jobs, "timestamp": time.time()}

        logger.info(f"Fetched {len(jobs)} live jobs for: {query}")
        return jobs

    except requests.exceptions.Timeout:
        logger.warning("JSearch API timed out")
        return []
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            logger.warning("JSearch API rate limit exceeded")
        else:
            logger.warning(f"JSearch API error: {e}")
        return []
    except Exception as e:
        logger.warning(f"JSearch API failed: {e}")
        return []


def _normalize_job(raw):
    """Convert a JSearch API job to our standard format."""
    try:
        title = raw.get("job_title", "")
        company = raw.get("employer_name", "Unknown")
        if not title:
            return None

        # Determine job type
        job_employment_type = raw.get("job_employment_type", "").upper()
        is_internship = (job_employment_type == "INTERN" or 
                         any(kw in title.lower() for kw in ["intern", "internship", "trainee"]))
        job_type = "internship" if is_internship else "full-time"

        # Location
        city = raw.get("job_city", "")
        state = raw.get("job_state", "")
        country = raw.get("job_country", "")
        location_parts = [p for p in [city, state, country] if p]
        location = ", ".join(location_parts) or "Remote"
        if raw.get("job_is_remote"):
            location = "Remote"

        # Salary
        min_sal = raw.get("job_min_salary")
        max_sal = raw.get("job_max_salary")
        if min_sal and max_sal:
            salary = f"${int(min_sal):,} — ${int(max_sal):,}"
        elif min_sal:
            salary = f"From ${int(min_sal):,}"
        else:
            salary = "Competitive"

        # Experience
        exp = raw.get("job_required_experience", {})
        exp_text = exp.get("required_experience_in_months")
        if exp_text and int(exp_text) > 36:
            exp_level = "Senior"
        elif exp_text and int(exp_text) > 12:
            exp_level = "Mid-level"
        else:
            exp_level = "Entry / Junior"

        # Required skills
        qualifications = raw.get("job_required_skills") or []

        return {
            "title": title,
            "company": company,
            "type": job_type,
            "location": location,
            "experience_level": exp_level,
            "description": raw.get("job_description", "")[:300],
            "salary_range": salary,
            "required_skills": [s.lower() for s in qualifications[:10]],
            "apply_url": (raw.get("job_apply_link") or (raw.get("job_apply_options") or [{}])[0].get("apply_link") or "#"),
            "source": "jsearch",
            "job_id": raw.get("job_id", ""),
            "posted": raw.get("job_posted_at_datetime_utc", ""),
            "employer_logo": raw.get("employer_logo", ""),
        }
    except Exception as e:
        logger.debug(f"Failed to normalize job: {e}")
        return None
