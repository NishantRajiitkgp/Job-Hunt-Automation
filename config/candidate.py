CANDIDATE = {
    "name": "Nishant Raj",
    "college": "IIT Kharagpur",
    "degree": "BS Physics",
    "graduation_year": 2026,
    "cgpa": 8.6,

    # Tech stack - be honest, this affects scoring accuracy
    "primary_stack": ["Next.js", "React", "TypeScript", "Node.js", "PostgreSQL"],
    "secondary_stack": ["Python", "FastAPI", "Docker", "Redis", "MongoDB", "AWS", "GCP"],
    "languages": ["TypeScript", "JavaScript", "C++", "Python", "SQL"],
    "dsa_problems": 700,
    "dsa_strength": "Strong",  # Strong / Medium / Weak

    # Job targets
    "target_salary_lpa": 12,
    "target_roles": [
        "Software Development Engineer",
        "SDE",
        "SDE I",
        "SDE 1",
        "Backend Engineer",
        "Full Stack Engineer",
        "Full Stack Developer",
        "Software Engineer",
        "Node.js Developer",
        "React Developer",
    ],
    "target_locations": [
        "Bangalore", "Bengaluru", "Mumbai", "Hyderabad",
        "Delhi NCR", "Noida", "Gurugram", "Pune", "Remote",
    ],
    "open_to_remote": True,

    # Blocklists - jobs matching these are skipped BEFORE Claude scoring (saves money)
    "avoid_companies": [
        "TCS", "Wipro", "HCL", "Cognizant", "Tech Mahindra",
        "Capgemini", "Mphasis", "Mindtree", "LTIMindtree",
        "Infosys", "Persistent Systems",
        "Aditi Consulting", "Expleo",
    ],
    "avoid_title_keywords": [
        "QA", "Testing", "Tester", "Support Engineer", "Data Entry",
        "Trainee", "Intern", "Manual", "ETL", "Mainframe",
        "SAP", "Salesforce Admin", ".NET", "Angular",
        "Low Code", "No Code", "Junior Developer",
        "Test Automation", "SDET",
    ],

    # Resume
    "resume_path": "./config/resume.txt",

    # Key experience highlights (fed to scorer for accurate matching)
    "resume_highlights": (
        "- 2 SDE internships (Canada remote): Full-stack + Backend\n"
        "- MindGuruYoga: Next.js 15, React 19, TypeScript, PostgreSQL/Supabase, GCP, CI/CD\n"
        "- TasklyApp.ai: Node.js, TypeScript, MongoDB, Redis, microservices, Docker, GCP Cloud Run\n"
        "- Built real-time sports dashboard with WebSockets, Express 5, PostgreSQL\n"
        "- Built flood detection platform under IIT KGP professor (Next.js, FastAPI, Docker, AWS S3)\n"
        "- Built AI stock platform (Next.js, MongoDB, Gemini AI, Inngest cron)\n"
        "- Strong DevOps: Docker, Kubernetes, GitHub Actions CI/CD, GCP, AWS, Terraform\n"
        "- 700+ DSA problems | C++ for competitive, TypeScript/Python for dev"
    ),
}
