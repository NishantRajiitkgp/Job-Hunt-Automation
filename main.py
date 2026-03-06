#!/usr/bin/env python3
"""Job Hunt OS — Master Orchestrator CLI."""

import argparse
import asyncio
import json
import os
import sys
from datetime import date, datetime, timezone

from dotenv import load_dotenv

load_dotenv()

# Fix Windows console Unicode output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from config.candidate import CANDIDATE
from scraper.naukri_scraper import scrape_naukri
from scraper.linkedin_scraper import scrape_linkedin
from prefilter.keyword_filter import should_skip
from prefilter.salary_estimator import estimate_salary
from scorer.gemini_scorer import score_jobs
from tracker.csv_tracker import save_csv, save_json, print_summary
from tracker.html_report import open_report, save_report

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SEEN_URLS_PATH = os.path.join(DATA_DIR, "seen_urls.json")


def _banner():
    today = date.today().isoformat()
    print("\u2554" + "\u2550" * 38 + "\u2557")
    print("\u2551        JOB HUNT OS v1.0              \u2551")
    print(f"\u2551  IIT KGP \u00d7 12L+ Target \u00d7 {today}   \u2551")
    print("\u255a" + "\u2550" * 38 + "\u255d")
    print()


def _load_seen_urls() -> set:
    if os.path.exists(SEEN_URLS_PATH):
        try:
            with open(SEEN_URLS_PATH, "r") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError):
            pass
    return set()


def _save_seen_urls(urls: set):
    os.makedirs(os.path.dirname(SEEN_URLS_PATH), exist_ok=True)
    with open(SEEN_URLS_PATH, "w") as f:
        json.dump(list(urls), f)


def _save_raw(jobs: list[dict], label: str):
    raw_dir = os.path.join(DATA_DIR, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    path = os.path.join(raw_dir, f"{label}_{date.today().isoformat()}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, default=str)
    return path


def _save_filtered(jobs: list[dict]):
    filt_dir = os.path.join(DATA_DIR, "filtered")
    os.makedirs(filt_dir, exist_ok=True)
    path = os.path.join(filt_dir, f"filtered_{date.today().isoformat()}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, default=str)
    return path


def _save_scored(jobs: list[dict]):
    scored_dir = os.path.join(DATA_DIR, "scored")
    os.makedirs(scored_dir, exist_ok=True)
    path = os.path.join(scored_dir, f"scored_{date.today().isoformat()}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, default=str)
    return path


def _load_latest(subdir: str) -> list[dict]:
    """Load the most recent JSON file from a data subdirectory."""
    target_dir = os.path.join(DATA_DIR, subdir)
    if not os.path.exists(target_dir):
        return []
    files = sorted(
        [f for f in os.listdir(target_dir) if f.endswith(".json")],
        reverse=True,
    )
    if not files:
        return []
    path = os.path.join(target_dir, files[0])
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


# ── Pipeline Steps ──────────────────────────────────────


async def step_scrape() -> list[dict]:
    """Scrape jobs from all sources."""
    print("\U0001f4e1 SCRAPING JOBS...")
    naukri_jobs, linkedin_jobs = await asyncio.gather(
        scrape_naukri(),
        scrape_linkedin(),
        return_exceptions=True,
    )

    all_jobs = []
    for result, name in [(naukri_jobs, "Naukri"), (linkedin_jobs, "LinkedIn")]:
        if isinstance(result, Exception):
            print(f"  \u26a0\ufe0f {name} scraper failed: {result}")
        else:
            all_jobs.extend(result)

    # Deduplicate by URL and by company+title (cross-source dedup)
    seen = set()
    seen_keys = set()
    deduped = []
    for job in all_jobs:
        if job["url"] in seen:
            continue
        key = f"{job['company'].lower().strip()}|{job['title'].lower().strip()}"
        if key in seen_keys:
            continue
        seen.add(job["url"])
        seen_keys.add(key)
        deduped.append(job)

    _save_raw(deduped, "scraped")
    print(f"  \u2705 Total scraped: {len(deduped)} unique jobs")
    return deduped


def step_dedup(jobs: list[dict]) -> list[dict]:
    """Remove jobs already seen in previous runs."""
    seen_urls = _load_seen_urls()
    new_jobs = [j for j in jobs if j["url"] not in seen_urls]
    already_seen = len(jobs) - len(new_jobs)
    print(f"  \U0001f50d Found {len(new_jobs)} new jobs, {already_seen} already seen")

    # Save new URLs
    new_urls = seen_urls | {j["url"] for j in new_jobs}
    _save_seen_urls(new_urls)

    return new_jobs


def step_prefilter(jobs: list[dict]) -> tuple[list[dict], int]:
    """Run keyword filter and salary estimator. Returns (passed_jobs, filtered_count)."""
    print("\n\U0001f50d PRE-FILTERING...")
    passed = []
    filtered_count = 0

    for job in jobs:
        # Keyword filter
        skip, reason = should_skip(job, CANDIDATE)
        if skip:
            job["prefilter_pass"] = False
            job["prefilter_reason"] = reason
            filtered_count += 1
            continue

        # Salary estimation
        min_lpa, max_lpa, confidence = estimate_salary(job["company"], job["salary_raw"])
        job["salary_estimate_lpa"] = f"{min_lpa}-{max_lpa}"
        job["salary_confidence"] = confidence

        # Filter out if estimated max salary is clearly too low
        if max_lpa < 8:
            job["prefilter_pass"] = False
            job["prefilter_reason"] = f"Salary too low: est {min_lpa}-{max_lpa}L"
            filtered_count += 1
            continue

        job["prefilter_pass"] = True
        job["prefilter_reason"] = "passed"
        passed.append(job)

    _save_filtered(passed)
    print(f"  \u2705 Pre-filter: {len(jobs)} total \u2192 {len(passed)} passed ({filtered_count} filtered out)")
    return passed, filtered_count


async def step_score(jobs: list[dict]) -> list[dict]:
    """Score filtered jobs with Gemini."""
    print(f"\n\U0001f9e0 SCORING {len(jobs)} JOBS...")
    scored = await score_jobs(jobs, CANDIDATE)
    _save_scored(scored)

    high = sum(1 for j in scored if j.get("score", 0) >= 75)
    good = sum(1 for j in scored if 65 <= j.get("score", 0) < 75)
    print(f"  \u2705 Scoring complete: {high} high match (75+), {good} good match (65-74)")
    return scored


def step_auto_apply(jobs: list[dict], min_score: int = 65) -> int:
    """Open high-scoring Naukri job URLs in browser for quick apply."""
    import webbrowser
    apply_jobs = [j for j in jobs if j.get("score", 0) >= min_score]
    if not apply_jobs:
        print(f"\n  No jobs scored {min_score}+ to apply for")
        return 0

    naukri_jobs = [j for j in apply_jobs if j.get("source") == "naukri"]
    linkedin_jobs = [j for j in apply_jobs if j.get("source") == "linkedin"]

    print(f"\n\U0001f680 AUTO-APPLY: {len(apply_jobs)} jobs scored {min_score}+")
    if naukri_jobs:
        print(f"  Opening {len(naukri_jobs)} Naukri jobs in browser (just click Apply)...")
        for j in naukri_jobs:
            scoring = j.get("scoring") or {}
            tier = scoring.get("tier", "")
            print(f"    [{j['score']}] {tier} | {j['company']} - {j['title']}")
            webbrowser.open(j["url"])
            j["status"] = "applied"

    if linkedin_jobs:
        print(f"  Opening {len(linkedin_jobs)} LinkedIn jobs in browser...")
        for j in linkedin_jobs:
            scoring = j.get("scoring") or {}
            tier = scoring.get("tier", "")
            print(f"    [{j['score']}] {tier} | {j['company']} - {j['title']}")
            webbrowser.open(j["url"])
            j["status"] = "applied"

    applied = len(naukri_jobs) + len(linkedin_jobs)
    print(f"  \u2705 Opened {applied} job pages in browser")
    return applied


def step_track(scored_jobs: list[dict]) -> tuple[str, str]:
    """Save results to CSV and JSON."""
    csv_path = save_csv(scored_jobs)
    json_path = save_json(scored_jobs)
    return csv_path, json_path


# ── CLI Modes ───────────────────────────────────────────


async def mode_scrape():
    """Scrape only."""
    jobs = await step_scrape()
    return jobs


async def mode_filter():
    """Pre-filter latest scraped data."""
    jobs = _load_latest("raw")
    if not jobs:
        print("  \u26a0\ufe0f No scraped data found. Run --mode scrape first.")
        return []
    passed, _ = step_prefilter(jobs)
    return passed


async def mode_score():
    """Score latest filtered data."""
    jobs = _load_latest("filtered")
    if not jobs:
        print("  \u26a0\ufe0f No filtered data found. Run --mode filter first.")
        return []
    scored = await step_score(jobs)
    return scored


async def mode_apply():
    """Auto-apply: open high-scoring jobs in browser."""
    jobs = _load_latest("scored")
    if not jobs:
        print("  \u26a0\ufe0f No scored data found. Run --mode score first.")
        return []
    step_auto_apply(jobs)
    csv_path, json_path = step_track(jobs)
    print(f"\n  \U0001f4c1 CSV:  {csv_path}")
    print(f"  \U0001f4c1 JSON: {json_path}")
    return jobs


async def mode_full():
    """Run entire pipeline from scratch."""
    # 1. Scrape
    all_jobs = await step_scrape()
    total_scraped = len(all_jobs)

    # 2. Dedup
    new_jobs = step_dedup(all_jobs)
    new_count = len(new_jobs)

    if not new_jobs:
        print("\n  \u2705 No new jobs to process!")
        return

    # 3. Pre-filter
    filtered_jobs, filtered_count = step_prefilter(new_jobs)
    sent_to_gemini = len(filtered_jobs)

    if not filtered_jobs:
        print("\n  \u2705 All jobs filtered out by pre-filter!")
        return

    # 4. Score
    scored_jobs = await step_score(filtered_jobs)

    # 5. Track + Report
    csv_path, json_path = step_track(scored_jobs)
    report_path = open_report(scored_jobs)

    # 6. Summary
    apply_count = sum(1 for j in scored_jobs if j.get("score", 0) >= 65)
    print_summary(
        total_scraped=total_scraped,
        new_jobs=new_count,
        filtered_out=filtered_count,
        sent_to_claude=sent_to_gemini,
        scored_jobs=scored_jobs,
        applications_ready=apply_count,
        csv_path=csv_path,
        json_path=json_path,
        estimated_cost=total_scraped * 0.001,
    )

    # 7. Auto-apply prompt
    if apply_count > 0:
        print(f"\n  \U0001f680 Run 'py main.py --mode apply' to open {apply_count} jobs in browser for quick apply!")


async def mode_rerun():
    """Daily use: scrape + only process NEW jobs."""
    await mode_full()


async def mode_report():
    """Generate and open HTML dashboard."""
    jobs = _load_latest("scored")
    if not jobs:
        print("  \u26a0\ufe0f No data found. Run the pipeline first.")
        return
    path = open_report(jobs)
    print(f"  \U0001f4c1 Report opened: {path}")


async def mode_stats():
    """Print stats on latest scored data."""
    scored = _load_latest("scored")
    if not scored:
        print("  \u26a0\ufe0f No scored/applied data found.")
        return

    print(f"\n\U0001f4ca STATS ({len(scored)} jobs)")
    print("\u2501" * 40)

    # Group by tier
    tiers = {}
    for j in scored:
        tier = (j.get("scoring") or {}).get("tier", "Skip")
        tiers.setdefault(tier, []).append(j)

    for tier_name in ["Dream SDE", "Strong SDE", "Worth Applying", "Skip"]:
        jobs_in_tier = tiers.get(tier_name, [])
        print(f"  {tier_name:16s}: {len(jobs_in_tier)}")

    applied = [j for j in scored if j.get("status") == "applied"]
    print(f"  Already applied:  {len(applied)}")

    top = sorted(scored, key=lambda j: j.get("score", 0), reverse=True)[:10]
    if top:
        print(f"\n  Top 10:")
        for j in top:
            scoring = j.get("scoring") or {}
            tier = scoring.get("tier", "")[:6]
            print(f"    {j['score']:3d} | {tier:6s} | {j['company'][:20]:20s} | {j['title'][:30]:30s}")

    # Source breakdown
    naukri = sum(1 for j in scored if j.get("source") == "naukri")
    linkedin = sum(1 for j in scored if j.get("source") == "linkedin")
    print(f"\n  Sources: Naukri={naukri}, LinkedIn={linkedin}")
    print("\u2501" * 40)


# ── Entry Point ─────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Job Hunt OS - Automated Job Hunting Pipeline")
    parser.add_argument(
        "--mode",
        choices=["scrape", "filter", "score", "apply", "full", "rerun", "stats", "report"],
        default="rerun",
        help="Pipeline mode (default: rerun)",
    )
    args = parser.parse_args()

    _banner()

    mode_map = {
        "scrape": mode_scrape,
        "filter": mode_filter,
        "score": mode_score,
        "apply": mode_apply,
        "full": mode_full,
        "rerun": mode_rerun,
        "report": mode_report,
        "stats": mode_stats,
    }

    asyncio.run(mode_map[args.mode]())


if __name__ == "__main__":
    main()
