import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone

import httpx

from .sources import APIFY_BASE, LINKEDIN_ACTOR

LINKEDIN_INPUT = {
    "urls": [
        "https://www.linkedin.com/jobs/search/?keywords=software%20development%20engineer&location=India&f_E=2&f_TPR=r604800",
        "https://www.linkedin.com/jobs/search/?keywords=SDE%20fresher&location=India&f_E=2&f_TPR=r604800",
        "https://www.linkedin.com/jobs/search/?keywords=software%20engineer%20new%20grad&location=India&f_E=2&f_TPR=r604800",
        "https://www.linkedin.com/jobs/search/?keywords=full%20stack%20developer&location=India&f_E=2&f_TPR=r604800",
        "https://www.linkedin.com/jobs/search/?keywords=backend%20engineer&location=India&f_E=2&f_TPR=r604800",
        "https://www.linkedin.com/jobs/search/?keywords=SDE%201&location=India&f_E=2&f_TPR=r604800",
        "https://www.linkedin.com/jobs/search/?keywords=associate%20software%20engineer&location=India&f_E=2&f_TPR=r604800",
    ],
    "count": 100,
    "scrapeCompany": False,
}

POLL_INTERVAL = 5
MAX_POLL_TIME = 300


def _job_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:12]


def _extract_skills(raw: dict) -> str:
    """Try to extract skills from LinkedIn job data."""
    # Some actors return skills directly
    skills = raw.get("skills") or raw.get("skillsList") or ""
    if isinstance(skills, list):
        return ", ".join(skills)
    if skills:
        return str(skills)
    # Fall back to criteria/insights if available
    criteria = raw.get("jobCriteria") or raw.get("criteria") or []
    if isinstance(criteria, list):
        return ", ".join(str(c) for c in criteria[:10])
    return ""


def _normalize(raw: dict) -> dict:
    url = raw.get("link") or raw.get("url") or raw.get("jobUrl") or ""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": _job_id(url) if url else _job_id(json.dumps(raw, default=str)),
        "title": raw.get("title") or "",
        "company": raw.get("companyName") or raw.get("company") or "",
        "location": raw.get("location") or "",
        "description": raw.get("descriptionText") or raw.get("description") or "",
        "salary_raw": raw.get("salary") or "Not disclosed",
        "skills_listed": _extract_skills(raw),
        "url": url,
        "apply_url": url,
        "posted_at": raw.get("postedAt") or raw.get("publishedAt") or "",
        "applicants": raw.get("applicantsCount") or "",
        "source": "linkedin",
        "scraped_at": now,
        "salary_estimate_lpa": None,
        "salary_confidence": None,
        "prefilter_pass": None,
        "prefilter_reason": None,
        "score": None,
        "scoring": None,
        "status": "new",
    }


async def scrape_linkedin() -> list[dict]:
    """Scrape LinkedIn Jobs via Apify. Returns normalized job dicts."""
    token = os.getenv("APIFY_TOKEN")
    if not token:
        print("  \u26a0\ufe0f APIFY_TOKEN not set, skipping LinkedIn scraper")
        return []

    print("  \U0001f4e1 Starting LinkedIn Jobs scraper...")
    async with httpx.AsyncClient(timeout=60) as client:
        # Start actor run
        url = f"{APIFY_BASE}/acts/{LINKEDIN_ACTOR}/runs?token={token}"
        try:
            resp = await client.post(url, json=LINKEDIN_INPUT)
            if resp.status_code != 201:
                print(f"  \u26a0\ufe0f LinkedIn actor start failed ({resp.status_code}): {resp.text[:200]}")
                return []
            data = resp.json()
            run_id = data["data"]["id"]
        except Exception as e:
            print(f"  \u26a0\ufe0f LinkedIn actor start error: {e}")
            return []

        # Poll for completion
        elapsed = 0
        dataset_id = None
        while elapsed < MAX_POLL_TIME:
            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL
            try:
                resp = await client.get(f"{APIFY_BASE}/actor-runs/{run_id}?token={token}")
                run_data = resp.json()
                status = run_data["data"]["status"]
                if status == "SUCCEEDED":
                    dataset_id = run_data["data"]["defaultDatasetId"]
                    break
                elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    print(f"  \u26a0\ufe0f LinkedIn run ended with status: {status}")
                    return []
            except Exception as e:
                print(f"  \u26a0\ufe0f Poll error: {e}")

        if not dataset_id:
            print(f"  \u26a0\ufe0f LinkedIn run timed out after {MAX_POLL_TIME}s")
            return []

        # Fetch results
        try:
            resp = await client.get(f"{APIFY_BASE}/datasets/{dataset_id}/items?token={token}")
            items = resp.json()
            if not isinstance(items, list):
                items = []
        except Exception as e:
            print(f"  \u26a0\ufe0f LinkedIn results fetch error: {e}")
            return []

    all_jobs = []
    seen_urls = set()
    seen_company_title = set()
    for raw in items:
        job = _normalize(raw)
        if not job["url"] or job["url"] in seen_urls:
            continue
        # Deduplicate same company+title posted in multiple locations
        key = f"{job['company'].lower().strip()}|{job['title'].lower().strip()}"
        if key in seen_company_title:
            continue
        seen_company_title.add(key)
        seen_urls.add(job["url"])
        all_jobs.append(job)

    print(f"  \u2705 LinkedIn: {len(all_jobs)} unique jobs scraped")
    return all_jobs
