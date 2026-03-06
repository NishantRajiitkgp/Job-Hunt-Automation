def should_skip(job: dict, candidate: dict) -> tuple[bool, str]:
    """Check if a job should be skipped based on title/company blocklists.
    Returns (should_skip: bool, reason: str).
    """
    title_lower = job["title"].lower()
    company_lower = job["company"].lower()

    # 1. Skip avoided companies
    for company in candidate["avoid_companies"]:
        if company.lower() in company_lower:
            return True, f"Blocked company: {company}"

    # 2. Skip avoided title keywords
    for keyword in candidate["avoid_title_keywords"]:
        if keyword.lower() in title_lower:
            return True, f"Blocked keyword in title: {keyword}"

    # 3. Skip if title doesn't match any SDE-like role loosely
    role_keywords = [
        "software", "developer", "engineer", "sde", "backend",
        "frontend", "full stack", "fullstack", "node", "react",
        "python", "web developer", "programming", "coder",
    ]
    if not any(kw in title_lower for kw in role_keywords):
        return True, f"Title doesn't match SDE roles: {job['title']}"

    # 4. Skip if experience requirement is clearly too high
    exp = job.get("experience") or ""
    if exp:
        try:
            min_exp = int(exp.split("-")[0].strip().split()[0])
            if min_exp > 2:
                return True, f"Requires {min_exp}+ years experience"
        except (ValueError, IndexError):
            pass

    # 5. Skip seniority levels that are clearly too high
    seniority_blocks = ["senior", "staff", "principal", "lead", "manager", "director", "vp ", "head of", "sr.", "sr "]
    for kw in seniority_blocks:
        if kw in title_lower:
            return True, f"Senior role: {job['title']}"

    # 6. Skip clearly irrelevant tech in title (not in description — title is explicit)
    irrelevant_title = ["devops", "sre", "data scientist", "data analyst", "ml engineer",
                        "ios developer", "android developer", "embedded", "firmware",
                        "security engineer", "network engineer", "dba", "database admin"]
    for kw in irrelevant_title:
        if kw in title_lower:
            return True, f"Irrelevant specialization: {kw}"

    return False, "passed"
