import re

TIER_1 = {
    "google", "microsoft", "amazon", "meta", "apple", "netflix", "uber",
    "atlassian", "adobe", "salesforce", "oracle", "walmart", "nvidia",
    "qualcomm", "samsung r&d", "de shaw", "tower research", "rubrik",
}

TIER_2 = {
    "flipkart", "meesho", "razorpay", "cred", "groww", "zepto",
    "swiggy", "zomato", "phonepe", "paytm", "juspay", "browserstack",
    "postman", "freshworks", "dream11", "coinswitch", "polygon",
    "grafana", "notion", "hashicorp", "intuit", "paypal",
    "goldman sachs", "morgan stanley", "jpmorgan", "barclays",
    "sprinklr", "nutanix", "cohesity", "druva", "chargebee",
    "clevertap", "moengage", "hasura", "zerodha",
    "slice", "jupiter", "khatabook", "sharechat", "koo",
}

TIER_2_5 = {
    "accenture",  # Accenture pays 8-12L for freshers, borderline but not blocked
}

TIER_3 = {
    "infosys", "tcs", "wipro", "hcl", "cognizant", "tech mahindra",
    "capgemini", "mphasis", "mindtree", "ltimindtree",
}


def estimate_salary(company_name: str, salary_raw: str) -> tuple[int, int, str]:
    """Returns (min_lpa, max_lpa, confidence)."""
    name = company_name.lower().strip()

    # 1. If salary string is present, parse it
    if salary_raw and salary_raw != "Not disclosed":
        match = re.search(r"(\d+)-(\d+)\s*Lac", salary_raw, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2)), "high"
        # Try "X LPA" format
        match = re.search(r"(\d+)\s*LPA", salary_raw, re.IGNORECASE)
        if match:
            val = int(match.group(1))
            return val, val + 5, "medium"

    # 2. Company tier matching
    for company in TIER_1:
        if company in name:
            return 18, 40, "high"

    for company in TIER_2:
        if company in name:
            return 12, 25, "medium"

    for company in TIER_2_5:
        if company in name:
            return 8, 12, "medium"

    for company in TIER_3:
        if company in name:
            return 3, 7, "high"  # Service companies pay 3-7L for freshers, well below 12L target

    # 3. Unknown — pass through but flag as unknown
    # We can't estimate so we let the scorer decide
    return 8, 20, "unknown"
