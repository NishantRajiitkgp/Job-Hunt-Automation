import asyncio
import json
import os

import httpx

MODEL = "gemini-2.5-flash"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_TOKENS = 8192
CONCURRENCY = 5
DELAY_BETWEEN = 1

SYSTEM_PROMPT = (
    "You are an expert SDE job evaluator for Indian tech hiring. "
    "Evaluate jobs on THREE dimensions: Role Quality, Company Quality, and Candidate Fit. "
    "Return ONLY valid JSON, no markdown fences."
)

# Known dream companies for SDE roles in India
DREAM_COMPANIES = {
    "google", "microsoft", "amazon", "meta", "apple", "netflix", "uber",
    "atlassian", "adobe", "salesforce", "nvidia", "qualcomm",
    "de shaw", "tower research", "rubrik", "databricks", "stripe",
    "flipkart", "razorpay", "cred", "zepto", "meesho",
    "swiggy", "zomato", "phonepe", "groww", "juspay",
    "browserstack", "postman", "freshworks", "dream11",
    "goldman sachs", "morgan stanley", "jpmorgan", "barclays",
    "sprinklr", "nutanix", "cohesity", "druva",
    "docusign", "mastercard", "visa", "blackrock", "copart",
    "tesco", "walmart", "intuit", "paypal", "oracle",
}


def _company_tier(company: str) -> str:
    name = company.lower().strip()
    for c in DREAM_COMPANIES:
        if c in name:
            return "Dream"
    return "Unknown"


def _build_user_prompt(job: dict, candidate: dict) -> str:
    primary = ", ".join(candidate["primary_stack"])
    secondary = ", ".join(candidate["secondary_stack"][:5])
    roles = ", ".join(candidate["target_roles"][:5])
    sal_est = job.get("salary_estimate_lpa") or "unknown"
    sal_conf = job.get("salary_confidence") or "unknown"
    languages = ", ".join(candidate.get("languages", []))
    resume_highlights = candidate.get("resume_highlights", "")
    company_tier = _company_tier(job["company"])

    return f"""=== CANDIDATE ===
{candidate['college']} | {candidate['degree']} final year {candidate['graduation_year']} | CGPA {candidate['cgpa']}
Languages: {languages}
Primary Stack: {primary}
Secondary: {secondary}
DSA: {candidate['dsa_strength']} ({candidate['dsa_problems']} problems solved)
Target: {candidate['target_salary_lpa']}L+ | Roles: {roles}

Key Experience:
{resume_highlights}

=== JOB ===
{job['title']} at {job['company']} ({company_tier} company) | {job['location']}
Salary: {job['salary_raw']} (Est: {sal_est}L, {sal_conf} conf)
Skills required: {job['skills_listed']}
JD: {job['description'][:1500]}

=== EVALUATE ON THREE DIMENSIONS ===
1. ROLE QUALITY (0-100): Is this a real SDE/developer role? Does the JD describe actual engineering work (building systems, writing code, designing architecture)? Or is it disguised support/testing/maintenance? Freshers-friendly? Good growth potential?
2. COMPANY QUALITY (0-100): Is this a reputable company? Would this look good on a resume? Product company > Service company. Funded startup > Unknown startup.
3. CANDIDATE FIT (0-100): How well does THIS candidate's stack, experience, and level match the JD?

=== RETURN JSON ONLY ===
{{
  "role_quality": <0-100>,
  "company_quality": <0-100>,
  "candidate_fit": <0-100>,
  "score": <weighted average: role_quality*0.35 + company_quality*0.30 + candidate_fit*0.35>,
  "tier": "<Dream SDE | Strong SDE | Worth Applying | Skip>",
  "salary_verdict": "<Definitely 12L+ | Likely 12L+ | Maybe 12L+ | Likely below 12L>",
  "role_type": "<Pure SDE | Full Stack | Backend | Frontend | Mixed/Hybrid | Not SDE>",
  "red_flags": ["<max 2 red flags: e.g. 'disguised support role', 'no engineering in JD', 'too senior'>"],
  "why_apply": "<1 sentence: the real reason to apply or not>",
  "missing_skills": ["<max 3 skills from JD candidate lacks>"],
  "ats_keywords": ["<top 5 exact keywords from JD for resume>"]
}}

TIER RULES:
- Dream SDE: score >= 80 AND (known top company OR role_quality >= 85)
- Strong SDE: score >= 70 AND role_quality >= 70
- Worth Applying: score >= 55 AND role_quality >= 60
- Skip: everything else"""


def _build_payload(job: dict, candidate: dict) -> dict:
    return {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {"role": "user", "parts": [{"text": _build_user_prompt(job, candidate)}]}
        ],
        "generationConfig": {
            "maxOutputTokens": MAX_TOKENS,
            "temperature": 0.3,
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }


def _parse_response(data: dict) -> dict:
    """Extract JSON scoring from Gemini response."""
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        return json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return {"error": f"Parse failed: {e}", "raw": str(data)[:300]}


async def _score_one(
    client: httpx.AsyncClient,
    url: str,
    job: dict,
    candidate: dict,
) -> dict:
    """Score a single job. Returns the job dict with score/scoring filled."""
    payload = _build_payload(job, candidate)
    max_retries = 3

    for attempt in range(max_retries):
        try:
            resp = await client.post(url, json=payload)

            if resp.status_code == 429:
                wait = 15 * (attempt + 1)
                print(f"    \u23f3 Rate limited, waiting {wait}s (attempt {attempt+1}/{max_retries})...")
                await asyncio.sleep(wait)
                continue

            if resp.status_code != 200:
                job["score"] = 0
                job["scoring"] = {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
                return job

            data = resp.json()
            scoring = _parse_response(data)
            if "error" in scoring:
                job["score"] = 0
                job["scoring"] = scoring
            else:
                job["score"] = scoring.get("score", 0)
                job["scoring"] = scoring
                job["status"] = "scored"
            return job

        except Exception as e:
            job["score"] = 0
            job["scoring"] = {"error": str(e)}
            return job

    # All retries exhausted
    job["score"] = 0
    job["scoring"] = {"error": "Rate limited after all retries"}
    return job


async def score_jobs(jobs: list[dict], candidate: dict) -> list[dict]:
    """Score a list of jobs using Gemini. Returns scored jobs sorted by score desc."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("  \u26a0\ufe0f GEMINI_API_KEY not set, skipping scoring")
        return jobs

    url = GEMINI_URL.format(model=MODEL) + f"?key={api_key}"

    # Split into already-scored and needs-scoring
    already_scored = [j for j in jobs if j.get("status") == "scored" and j.get("score", 0) > 0]
    to_score = [j for j in jobs if j not in already_scored]

    total = len(to_score)
    if already_scored:
        print(f"  \u2705 Skipping {len(already_scored)} already-scored jobs")
    if total == 0:
        print("  \u2705 All jobs already scored!")
        return sorted(already_scored, key=lambda j: j.get("score", 0), reverse=True)

    print(f"  \U0001f9e0 Scoring {total} jobs with Gemini 2.5 Flash...")
    print(f"    Concurrency: {CONCURRENCY} | ~{total * DELAY_BETWEEN / CONCURRENCY / 60:.1f} min estimated")

    scored = list(already_scored)
    best_score = max((j.get("score", 0) for j in already_scored), default=0)
    best_company = next((j["company"] for j in already_scored if j.get("score", 0) == best_score), "") if best_score > 0 else ""

    async with httpx.AsyncClient(timeout=120) as client:
        sem = asyncio.Semaphore(CONCURRENCY)

        async def _bounded_score(job):
            async with sem:
                result = await _score_one(client, url, job, candidate)
                await asyncio.sleep(DELAY_BETWEEN)
                return result

        tasks = [asyncio.create_task(_bounded_score(j)) for j in to_score]
        done = 0
        for coro in asyncio.as_completed(tasks):
            result = await coro
            scored.append(result)
            done += 1

            if result["score"] > best_score:
                best_score = result["score"]
                best_company = result["company"]

            if done % 5 == 0 or done == total:
                tier = (result.get("scoring") or {}).get("tier", "")
                print(f"    \U0001f9e0 Scored {done}/{total} | Best: {best_company} ({best_score}) | Last: {tier}")

    scored.sort(key=lambda j: j.get("score", 0), reverse=True)
    return scored
