"""Generate a polished dark-mode HTML dashboard with tier-based job grouping."""

import os
import webbrowser
from datetime import date


TIER_ORDER = ["Dream SDE", "Strong SDE", "Worth Applying", "Skip"]
TIER_COLORS = {
    "Dream SDE": "#a78bfa",
    "Strong SDE": "#34d399",
    "Worth Applying": "#fbbf24",
    "Skip": "#64748b",
}
TIER_ICONS = {
    "Dream SDE": "&#9733;",   # star
    "Strong SDE": "&#9650;",  # triangle up
    "Worth Applying": "&#9679;",  # circle
    "Skip": "&#9644;",        # dash
}


def _score_color(score: int) -> str:
    if score >= 80:
        return "#a78bfa"
    if score >= 70:
        return "#34d399"
    if score >= 55:
        return "#fbbf24"
    return "#f87171"


def _esc(text) -> str:
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _build_card(j: dict, idx: int) -> str:
    score = j.get("score", 0)
    scoring = j.get("scoring") or {}
    color = _score_color(score)
    tier = scoring.get("tier", "Skip")
    tier_color = TIER_COLORS.get(tier, "#64748b")
    role_type = scoring.get("role_type", "")

    # Red flags
    red_flags = scoring.get("red_flags", [])
    flags_html = "".join(f'<span class="chip chip-red">{_esc(f)}</span>' for f in red_flags[:2])

    # Missing skills
    missing = scoring.get("missing_skills", [])
    missing_html = "".join(f'<span class="chip chip-orange">{_esc(s)}</span>' for s in missing[:3])

    # ATS keywords
    ats = scoring.get("ats_keywords", [])
    ats_html = "".join(f'<span class="chip chip-blue">{_esc(s)}</span>' for s in ats[:5])

    # Salary verdict
    salary_verdict = scoring.get("salary_verdict", "")
    if "Definitely" in salary_verdict:
        sv_cls = "tag-green"
    elif "Likely 12L+" in salary_verdict:
        sv_cls = "tag-yellow"
    elif "Maybe" in salary_verdict:
        sv_cls = "tag-orange"
    else:
        sv_cls = "tag-red"

    # Sub-scores
    rq = scoring.get("role_quality", 0)
    cq = scoring.get("company_quality", 0)
    cf = scoring.get("candidate_fit", 0)

    source = j.get("source", "")
    source_cls = "tag-naukri" if source == "naukri" else "tag-linkedin"

    why_apply = scoring.get("why_apply", "")

    return f'''
    <div class="job-card" data-score="{score}" data-source="{_esc(source)}" data-tier="{_esc(tier)}">
        <div class="card-header">
            <div class="score-badge" style="--accent:{color}">
                <span class="score-num">{score}</span>
            </div>
            <div class="card-info">
                <h3 class="job-title">{_esc(j["title"])}</h3>
                <p class="job-meta">{_esc(j["company"])} <span class="dot"></span> {_esc(j["location"])}</p>
            </div>
            <div class="card-tags">
                <span class="tier-badge" style="--tier-color:{tier_color}">{TIER_ICONS.get(tier, "")} {_esc(tier)}</span>
                {f'<span class="tag tag-role">{_esc(role_type)}</span>' if role_type else ''}
                <span class="tag {sv_cls}">{_esc(salary_verdict)}</span>
                <span class="tag {source_cls}">{_esc(source)}</span>
            </div>
        </div>
        <div class="card-body">
            <div class="sub-scores">
                <div class="sub-score"><span class="sub-label">Role</span><span class="sub-val" style="color:{_score_color(rq)}">{rq}</span></div>
                <div class="sub-score"><span class="sub-label">Company</span><span class="sub-val" style="color:{_score_color(cq)}">{cq}</span></div>
                <div class="sub-score"><span class="sub-label">Fit</span><span class="sub-val" style="color:{_score_color(cf)}">{cf}</span></div>
                <div class="sub-score wide"><span class="sub-label">Salary</span><span class="sub-val">{_esc(j.get("salary_raw", "N/A"))}</span></div>
            </div>
            {f'<p class="why-apply">{_esc(why_apply)}</p>' if why_apply else ''}
            <div class="chips-section">
                {f'<div class="chips-row"><span class="chips-label">Red Flags</span>{flags_html}</div>' if flags_html else ''}
                {f'<div class="chips-row"><span class="chips-label">Missing</span>{missing_html}</div>' if missing_html else ''}
                {f'<div class="chips-row"><span class="chips-label">ATS Keywords</span>{ats_html}</div>' if ats_html else ''}
            </div>
            <a href="{_esc(j.get('apply_url') or j.get('url', ''))}" target="_blank" class="apply-link">
                Open Job Listing
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 17L17 7M17 7H7M17 7v10"/></svg>
            </a>
        </div>
    </div>'''


def generate_html(jobs: list[dict]) -> str:
    today = date.today().isoformat()
    scored = [j for j in jobs if j.get("score", 0) > 0]
    scored.sort(key=lambda j: j.get("score", 0), reverse=True)

    # Group by tier
    tier_groups = {t: [] for t in TIER_ORDER}
    for j in scored:
        tier = (j.get("scoring") or {}).get("tier", "Skip")
        if tier not in tier_groups:
            tier = "Skip"
        tier_groups[tier].append(j)

    naukri = sum(1 for j in scored if j.get("source") == "naukri")
    linkedin = sum(1 for j in scored if j.get("source") == "linkedin")

    # Build tier sections
    cards_html = ""
    for idx_offset, tier_name in enumerate(TIER_ORDER):
        tier_jobs = tier_groups[tier_name]
        if not tier_jobs:
            continue
        tier_color = TIER_COLORS[tier_name]
        cards_html += f'''
        <div class="tier-section" data-tier-section="{_esc(tier_name)}">
            <div class="tier-header">
                <span class="tier-icon" style="color:{tier_color}">{TIER_ICONS[tier_name]}</span>
                <h2 class="tier-title" style="color:{tier_color}">{_esc(tier_name)}</h2>
                <span class="tier-count">{len(tier_jobs)} jobs</span>
            </div>'''
        for i, j in enumerate(tier_jobs):
            cards_html += _build_card(j, idx_offset * 1000 + i)
        cards_html += '</div>'

    if not cards_html:
        cards_html = '<div class="empty">No scored jobs yet. Run the pipeline first.</div>'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Job Hunt OS - {today}</title>
<style>
:root {{
    --bg: #0a0a0f;
    --bg-card: #12121a;
    --bg-elevated: #1a1a25;
    --bg-hover: #1e1e2a;
    --border: #ffffff0d;
    --border-light: #ffffff1a;
    --text: #e2e8f0;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --accent: #818cf8;
    --accent-dim: #818cf820;
    --green: #34d399;
    --yellow: #fbbf24;
    --orange: #fb923c;
    --red: #f87171;
    --purple: #a78bfa;
    --blue: #60a5fa;
    --radius: 12px;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }}
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.hero {{
    position: relative;
    padding: 48px 24px 72px;
    text-align: center;
    overflow: hidden;
    background: linear-gradient(180deg, #1a1040 0%, var(--bg) 100%);
}}
.hero::before {{
    content: '';
    position: absolute;
    top: -50%;
    left: 50%;
    transform: translateX(-50%);
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, #818cf830 0%, transparent 70%);
    pointer-events: none;
}}
.hero h1 {{
    font-size: 36px;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #c7d2fe, #818cf8, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 6px;
    position: relative;
}}
.hero .subtitle {{
    color: var(--text-muted);
    font-size: 14px;
    font-weight: 500;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    position: relative;
}}

/* Stats Grid */
.stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
    max-width: 960px;
    margin: -44px auto 0;
    padding: 0 20px;
    position: relative;
    z-index: 1;
}}
.stat-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px 16px;
    text-align: center;
    transition: all 0.2s;
}}
.stat-card:hover {{
    border-color: var(--border-light);
    transform: translateY(-2px);
}}
.stat-num {{
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1;
}}
.stat-label {{
    font-size: 10px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 6px;
}}

/* Filters */
.filter-bar {{
    max-width: 960px;
    margin: 24px auto 16px;
    padding: 0 20px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}}
.fbtn {{
    padding: 7px 16px;
    border-radius: 999px;
    border: 1px solid var(--border-light);
    background: transparent;
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    font-family: inherit;
    transition: all 0.15s;
}}
.fbtn:hover {{ background: var(--bg-elevated); color: var(--text); }}
.fbtn.active {{
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
}}

/* Tier Sections */
.cards-container {{
    max-width: 960px;
    margin: 0 auto;
    padding: 0 20px 60px;
}}
.tier-section {{
    margin-bottom: 32px;
}}
.tier-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 16px 0 12px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 12px;
}}
.tier-icon {{
    font-size: 18px;
}}
.tier-title {{
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.01em;
}}
.tier-count {{
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 500;
    margin-left: auto;
}}

/* Cards */
.job-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    margin-bottom: 10px;
    overflow: hidden;
    transition: all 0.2s;
}}
.job-card:hover {{
    border-color: var(--border-light);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}}
.card-header {{
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 18px 18px 0;
    flex-wrap: wrap;
}}
.score-badge {{
    width: 48px;
    height: 48px;
    border-radius: 12px;
    background: color-mix(in srgb, var(--accent) 12%, transparent);
    border: 2px solid color-mix(in srgb, var(--accent) 30%, transparent);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}}
.score-num {{
    font-size: 18px;
    font-weight: 800;
    color: var(--accent);
}}
.card-info {{ flex: 1; min-width: 180px; }}
.job-title {{
    font-size: 15px;
    font-weight: 600;
    color: var(--text);
    line-height: 1.3;
}}
.job-meta {{
    color: var(--text-muted);
    font-size: 13px;
    margin-top: 2px;
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
}}
.dot {{ width: 3px; height: 3px; border-radius: 50%; background: var(--text-muted); }}
.card-tags {{
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    align-items: flex-start;
}}
.tier-badge {{
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    white-space: nowrap;
    background: color-mix(in srgb, var(--tier-color) 15%, transparent);
    color: var(--tier-color);
    border: 1px solid color-mix(in srgb, var(--tier-color) 25%, transparent);
}}
.tag {{
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    white-space: nowrap;
}}
.tag-green {{ background: #34d39915; color: var(--green); }}
.tag-yellow {{ background: #fbbf2415; color: var(--yellow); }}
.tag-orange {{ background: #fb923c15; color: var(--orange); }}
.tag-red {{ background: #f8717115; color: var(--red); }}
.tag-muted {{ background: var(--bg-elevated); color: var(--text-muted); }}
.tag-role {{ background: #818cf815; color: var(--accent); }}
.tag-naukri {{ background: #06b6d415; color: #22d3ee; }}
.tag-linkedin {{ background: #3b82f615; color: #60a5fa; }}

.card-body {{ padding: 14px 18px 18px; }}

/* Sub-scores row */
.sub-scores {{
    display: flex;
    gap: 16px;
    padding: 10px 0;
    border-top: 1px solid var(--border);
    flex-wrap: wrap;
}}
.sub-score {{
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 60px;
}}
.sub-score.wide {{ min-width: 100px; }}
.sub-label {{ font-size: 10px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }}
.sub-val {{ font-size: 14px; font-weight: 700; color: var(--text-secondary); }}

.why-apply {{
    font-size: 13px;
    color: var(--green);
    padding: 8px 0 4px;
    line-height: 1.4;
    font-weight: 500;
}}

.chips-section {{ padding: 6px 0 0; }}
.chips-row {{ display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 6px; }}
.chips-label {{ font-size: 10px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; margin-right: 4px; }}
.chip {{
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 500;
}}
.chip-red {{ background: #f8717112; color: #fca5a5; }}
.chip-orange {{ background: #fb923c12; color: #fdba74; }}
.chip-blue {{ background: #818cf812; color: #a5b4fc; }}

.apply-link {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--accent);
    text-decoration: none;
    font-size: 13px;
    font-weight: 500;
    margin-top: 8px;
    padding: 6px 0;
    transition: opacity 0.15s;
}}
.apply-link:hover {{ opacity: 0.8; }}

.empty {{ text-align: center; padding: 60px 20px; color: var(--text-muted); font-size: 16px; }}

@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: translateY(0); }} }}
::-webkit-scrollbar {{ width: 8px; }}
::-webkit-scrollbar-track {{ background: var(--bg); }}
::-webkit-scrollbar-thumb {{ background: #333; border-radius: 4px; }}
</style>
</head>
<body>

<div class="hero">
    <h1>Job Hunt OS</h1>
    <p class="subtitle">IIT KGP &bull; SDE Roles &bull; 12L+ Target &bull; {today}</p>
</div>

<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-num" style="color:var(--purple)">{len(tier_groups["Dream SDE"])}</div>
        <div class="stat-label">Dream SDE</div>
    </div>
    <div class="stat-card">
        <div class="stat-num" style="color:var(--green)">{len(tier_groups["Strong SDE"])}</div>
        <div class="stat-label">Strong SDE</div>
    </div>
    <div class="stat-card">
        <div class="stat-num" style="color:var(--yellow)">{len(tier_groups["Worth Applying"])}</div>
        <div class="stat-label">Worth Applying</div>
    </div>
    <div class="stat-card">
        <div class="stat-num" style="color:var(--text-muted)">{len(tier_groups["Skip"])}</div>
        <div class="stat-label">Skip</div>
    </div>
    <div class="stat-card">
        <div class="stat-num" style="color:var(--text)">{len(scored)}</div>
        <div class="stat-label">Total Scored</div>
    </div>
    <div class="stat-card">
        <div class="stat-num" style="color:#22d3ee">{naukri}</div>
        <div class="stat-label">Naukri</div>
    </div>
    <div class="stat-card">
        <div class="stat-num" style="color:var(--blue)">{linkedin}</div>
        <div class="stat-label">LinkedIn</div>
    </div>
</div>

<div class="filter-bar">
    <button class="fbtn active" onclick="filterJobs('all',this)">All ({len(scored)})</button>
    <button class="fbtn" onclick="filterJobs('Dream SDE',this)">Dream ({len(tier_groups["Dream SDE"])})</button>
    <button class="fbtn" onclick="filterJobs('Strong SDE',this)">Strong ({len(tier_groups["Strong SDE"])})</button>
    <button class="fbtn" onclick="filterJobs('Worth Applying',this)">Worth ({len(tier_groups["Worth Applying"])})</button>
    <button class="fbtn" onclick="filterJobs('naukri',this)">Naukri ({naukri})</button>
    <button class="fbtn" onclick="filterJobs('linkedin',this)">LinkedIn ({linkedin})</button>
</div>

<div class="cards-container" id="cards">
    {cards_html}
</div>

<script>
function filterJobs(f, btn) {{
    document.querySelectorAll('.fbtn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.job-card').forEach(c => {{
        const tier = c.dataset.tier;
        const src = c.dataset.source;
        let show = true;
        if (f === 'naukri') show = src === 'naukri';
        else if (f === 'linkedin') show = src === 'linkedin';
        else if (f !== 'all') show = tier === f;
        c.style.display = show ? '' : 'none';
    }});
    // Show/hide tier section headers
    document.querySelectorAll('.tier-section').forEach(sec => {{
        const cards = sec.querySelectorAll('.job-card');
        const anyVisible = Array.from(cards).some(c => c.style.display !== 'none');
        sec.style.display = anyVisible ? '' : 'none';
    }});
}}
</script>
</body>
</html>'''
    return html


def save_report(jobs: list[dict]) -> str:
    """Generate HTML report and return its path."""
    report_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reports")
    os.makedirs(report_dir, exist_ok=True)
    path = os.path.join(report_dir, f"report_{date.today().isoformat()}.html")
    html = generate_html(jobs)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def open_report(jobs: list[dict]):
    """Generate and open the HTML report in default browser."""
    path = save_report(jobs)
    webbrowser.open(f"file://{os.path.abspath(path)}")
    return path
