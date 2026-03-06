import csv
import json
import os
from datetime import date

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "applied")

CSV_COLUMNS = [
    "Score", "Company", "Role", "Location", "Salary", "Salary Verdict",
    "Source", "Apply URL", "Status", "ATS Keywords", "Top Reason", "Top Concern",
]


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _job_to_row(job: dict) -> dict:
    scoring = job.get("scoring") or {}
    return {
        "Score": job.get("score", 0),
        "Company": job.get("company", ""),
        "Role": job.get("title", ""),
        "Location": job.get("location", ""),
        "Salary": job.get("salary_raw", ""),
        "Salary Verdict": scoring.get("salary_verdict", ""),
        "Source": job.get("source", ""),
        "Apply URL": job.get("url", ""),
        "Status": job.get("status", "new"),
        "ATS Keywords": ", ".join(scoring.get("ats_keywords", [])),
        "Top Reason": scoring.get("top_reason", ""),
        "Top Concern": scoring.get("top_concern", ""),
    }


def save_csv(jobs: list[dict], filename: str | None = None) -> str:
    """Save scored jobs to CSV. Returns the file path."""
    _ensure_dir()
    if not filename:
        filename = f"jobs_{date.today().isoformat()}.csv"
    path = os.path.join(DATA_DIR, filename)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for job in jobs:
            writer.writerow(_job_to_row(job))

    return path


def save_json(jobs: list[dict], filename: str | None = None) -> str:
    """Save full job data to JSON. Returns the file path."""
    _ensure_dir()
    if not filename:
        filename = f"applications_{date.today().isoformat()}.json"
    path = os.path.join(DATA_DIR, filename)

    # Merge with existing data if file exists
    existing = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = []

    # Deduplicate by job id
    seen_ids = {j["id"] for j in existing}
    for job in jobs:
        if job["id"] not in seen_ids:
            existing.append(job)
            seen_ids.add(job["id"])

    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, default=str)

    return path


def print_summary(
    total_scraped: int,
    new_jobs: int,
    filtered_out: int,
    sent_to_claude: int,
    scored_jobs: list[dict],
    applications_ready: int,
    csv_path: str,
    json_path: str,
    estimated_cost: float,
):
    """Print the pipeline summary to console."""
    high = sum(1 for j in scored_jobs if j.get("score", 0) >= 75)
    good = sum(1 for j in scored_jobs if 65 <= j.get("score", 0) < 75)
    low = sum(1 for j in scored_jobs if j.get("score", 0) < 65)

    print("\n" + "\u2501" * 40)
    print("\U0001f4ca PIPELINE COMPLETE")
    print("\u2501" * 40)
    print(f"  Scraped:           {total_scraped} jobs ({new_jobs} new)")
    print(f"  Pre-filtered out:  {filtered_out} (blocked companies/titles/salary)")
    print(f"  Sent to Gemini:    {sent_to_claude}")
    print(f"  High match (75+):  {high}  \u2190 apply TODAY")
    print(f"  Good match (65-74):{good}  \u2190 apply this week")
    print(f"  Low match (<65):   {low}  \u2190 skip")
    print()
    print(f"  Applications ready: {applications_ready}")
    print(f"  Estimated cost:     ~${estimated_cost:.2f}")
    print()
    print(f"  \U0001f4c1 CSV:  {csv_path}")
    print(f"  \U0001f4c1 JSON: {json_path}")
    print("\u2501" * 40)
