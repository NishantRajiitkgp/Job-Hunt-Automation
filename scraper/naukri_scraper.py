import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone

import httpx

from .sources import APIFY_BASE, NAUKRI_ACTOR

# Broad SDE searches + specific high-signal queries
_BASE = {
    "freshness": "7",
    "sortBy": "date",
    "experience": "0",
    "salaryRange": ["10to15", "15to25"],
    "department": ["5"],
    "fetchDetails": True,
}

SEARCH_CONFIGS = [
    # Broad SDE searches
    {**_BASE, "keyword": "SDE fresher", "maxJobs": 100},
    {**_BASE, "keyword": "software engineer 0-2 years", "maxJobs": 100},
    {**_BASE, "keyword": "software development engineer", "maxJobs": 100},
    # Stack-specific (your strongest skills)
    {**_BASE, "keyword": "full stack developer node.js react", "maxJobs": 75},
    {**_BASE, "keyword": "backend developer node.js", "maxJobs": 75},
    # Role-specific
    {**_BASE, "keyword": "SDE 1", "maxJobs": 50},
    {**_BASE, "keyword": "associate software engineer", "maxJobs": 50},
]

POLL_INTERVAL = 5
MAX_POLL_TIME = 300  # 5 minutes


def _job_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:12]


def _normalize(raw: dict) -> dict:
    url = raw.get("jdURL") or raw.get("jobUrl") or raw.get("url") or ""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": _job_id(url) if url else _job_id(json.dumps(raw, default=str)),
        "title": raw.get("title") or "",
        "company": raw.get("companyName") or raw.get("company") or "",
        "location": raw.get("location") or "",
        "description": raw.get("jobDescription") or raw.get("description") or "",
        "salary_raw": raw.get("salary") or "Not disclosed",
        "skills_listed": raw.get("tagsAndSkills") or raw.get("skills") or "",
        "url": url,
        "apply_url": url,
        "posted_at": raw.get("createdDate") or raw.get("postedDate") or "",
        "applicants": raw.get("applicants") or "",
        "source": "naukri",
        "scraped_at": now,
        "salary_estimate_lpa": None,
        "salary_confidence": None,
        "prefilter_pass": None,
        "prefilter_reason": None,
        "score": None,
        "scoring": None,
        "status": "new",
    }


async def _run_actor(client: httpx.AsyncClient, token: str, config: dict) -> list[dict]:
    """Start an Apify actor run, poll for completion, return results."""
    url = f"{APIFY_BASE}/acts/{NAUKRI_ACTOR}/runs?token={token}"
    try:
        resp = await client.post(url, json=config)
        if resp.status_code != 201:
            print(f"  \u26a0\ufe0f Naukri actor start failed ({resp.status_code}): {resp.text[:200]}")
            return []
        data = resp.json()
        run_id = data["data"]["id"]
    except Exception as e:
        print(f"  \u26a0\ufe0f Naukri actor start error: {e}")
        return []

    # Poll for completion
    elapsed = 0
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
                print(f"  \u26a0\ufe0f Naukri run {run_id} ended with status: {status}")
                return []
        except Exception as e:
            print(f"  \u26a0\ufe0f Poll error: {e}")
    else:
        print(f"  \u26a0\ufe0f Naukri run {run_id} timed out after {MAX_POLL_TIME}s")
        return []

    # Fetch results
    try:
        resp = await client.get(f"{APIFY_BASE}/datasets/{dataset_id}/items?token={token}")
        items = resp.json()
        return items if isinstance(items, list) else []
    except Exception as e:
        print(f"  \u26a0\ufe0f Naukri results fetch error: {e}")
        return []


async def scrape_naukri() -> list[dict]:
    """Scrape Naukri.com via Apify. Returns normalized job dicts."""
    token = os.getenv("APIFY_TOKEN")
    if not token:
        print("  \u26a0\ufe0f APIFY_TOKEN not set, skipping Naukri scraper")
        return []

    print(f"  \U0001f4e1 Starting {len(SEARCH_CONFIGS)} Naukri searches in parallel...")
    async with httpx.AsyncClient(timeout=60) as client:
        tasks = [_run_actor(client, token, cfg) for cfg in SEARCH_CONFIGS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs = []
    seen_urls = set()
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"  \u26a0\ufe0f Search {i+1} failed: {result}")
            continue
        for raw in result:
            job = _normalize(raw)
            if job["url"] and job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                all_jobs.append(job)

    print(f"  \u2705 Naukri: {len(all_jobs)} unique jobs scraped")
    return all_jobs
