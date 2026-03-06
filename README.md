# Job Hunt OS

Automated job hunting pipeline for Indian SDE roles. Scrapes Naukri + LinkedIn via Apify, pre-filters junk, AI-scores every job on 3 dimensions using Gemini 2.5 Flash, and serves a dark-mode dashboard with tier-based rankings. One command, zero manual filtering.

## How It Works

```
Naukri + LinkedIn  -->  Pre-filter  -->  Gemini Score  -->  Dashboard + Auto-Apply
   (Apify API)        keyword/salary    3-dim scoring       tier-ranked HTML
   7+7 queries        blocks junk       Role + Company      Dream / Strong /
   ~500 jobs/run      ~60% removed      + Candidate Fit     Worth / Skip
```

**Scoring is 3-dimensional:**
| Dimension | Weight | What it measures |
|---|---|---|
| Role Quality | 35% | Is this real SDE work? Growth potential? |
| Company Quality | 30% | Reputation, product vs service, funding |
| Candidate Fit | 35% | Stack match, experience level, skills gap |

**Jobs are tiered, not just numbered:**
- **Dream SDE** — Score 80+ at a top company (Google, Flipkart, Razorpay, etc.)
- **Strong SDE** — Score 70+ with solid role quality
- **Worth Applying** — Score 55+ with decent engineering work
- **Skip** — Everything else

## Setup

1. **Clone and install:**
   ```bash
   git clone https://github.com/<your-username>/job-hunt-os.git
   cd job-hunt-os
   pip install -r requirements.txt
   ```

2. **Configure API keys:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your keys:
   - `GEMINI_API_KEY` — [Google AI Studio](https://aistudio.google.com) -> Get API Key (FREE tier available)
   - `APIFY_TOKEN` — [Apify](https://apify.com) -> Settings -> Integrations ($5 free credit on signup)

3. **Edit your profile:**
   - `config/candidate.py` — your stack, target roles, salary target, company blocklist
   - `config/resume.txt` — paste your plain-text resume (fed to scorer for accurate matching)

4. **Run:**
   ```bash
   python main.py --mode full
   ```

## Daily Usage

```bash
python main.py --mode rerun
```

Scrapes fresh jobs, skips already-seen ones, pre-filters, scores with Gemini, and opens the dashboard. Only processes new jobs, so daily runs are fast and cheap.

## CLI Modes

| Mode | What it does |
|---|---|
| `--mode full` | Full pipeline: scrape + filter + score + dashboard |
| `--mode rerun` | Same as full (daily use — skips seen jobs) |
| `--mode scrape` | Scrape Naukri + LinkedIn only |
| `--mode filter` | Pre-filter latest scraped data |
| `--mode score` | AI-score filtered jobs with Gemini |
| `--mode apply` | Open 65+ scored jobs in browser for quick apply |
| `--mode report` | Regenerate and open the HTML dashboard |
| `--mode stats` | Print tier breakdown and top 10 jobs |

## Auto-Apply

```bash
python main.py --mode apply
```

Opens all jobs scoring 65+ directly in your browser — Naukri and LinkedIn. Just click Apply on each tab. No copy-pasting URLs.

## Project Structure

```
job-hunt-os/
├── main.py                  # CLI orchestrator
├── config/
│   ├── candidate.py         # Your profile, stack, blocklists
│   └── resume.txt           # Plain-text resume
├── scraper/
│   ├── naukri_scraper.py    # 7 search queries via Apify
│   ├── linkedin_scraper.py  # 7 search queries via Apify
│   └── sources.py           # Actor IDs, city codes
├── prefilter/
│   ├── keyword_filter.py    # Title/company/seniority blocklist
│   └── salary_estimator.py  # Company-tier salary estimation
├── scorer/
│   └── gemini_scorer.py     # 3-dimension Gemini 2.5 Flash scorer
├── tracker/
│   ├── html_report.py       # Dark-mode tier-grouped dashboard
│   └── csv_tracker.py       # CSV + JSON export
├── data/                    # Generated data (gitignored)
│   ├── raw/                 # Raw scraped JSON
│   ├── filtered/            # Post-prefilter JSON
│   ├── scored/              # Scored JSON
│   ├── reports/             # HTML dashboards
│   └── seen_urls.json       # Dedup tracker
├── .env.example
├── requirements.txt
└── .gitignore
```

## Customization

**Target different roles:** Edit `target_roles` in `config/candidate.py` and update search keywords in `scraper/naukri_scraper.py` and `scraper/linkedin_scraper.py`.

**Change salary threshold:** Update `target_salary_lpa` in `config/candidate.py`. The prefilter uses company tiers in `prefilter/salary_estimator.py` to estimate and block low-paying jobs.

**Block companies:** Add to `avoid_companies` in `config/candidate.py`. Service companies (TCS, Wipro, etc.) are blocked by default.

**Adjust scoring:** The scorer prompt and tier rules are in `scorer/gemini_scorer.py`. Dream companies list is there too.

## Cost

| Component | Cost |
|---|---|
| Naukri scrape (~450 jobs) | ~$0.10 |
| LinkedIn scrape (~100 jobs) | ~$0.10 |
| Gemini 2.5 Flash scoring | **FREE** |
| **Total per run** | **~$0.20** |

Gemini 2.5 Flash is free via Google AI Studio. The only cost is Apify scraping (~$0.20/run). Daily reruns cost less since deduplication skips already-seen jobs.

## Cron Job (Optional)

```bash
# Run daily at 8 AM IST (2:30 AM UTC)
30 2 * * * cd /path/to/job-hunt-os && python main.py --mode rerun >> logs/daily.log 2>&1
```

## Tech Stack

- **Python 3.11+** — asyncio for concurrent scraping + scoring
- **Gemini 2.5 Flash** — AI scoring via REST API (free tier)
- **Apify** — Naukri + LinkedIn scraping (verified actors, 96-99% success rate)
- **httpx** — async HTTP client
- **Zero frameworks** — no Django, no Flask, just a CLI script

## License

MIT
