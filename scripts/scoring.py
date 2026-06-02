"""
Keyword-based relevance scoring for Lionsys Solutions.
Returns score 0-100. Opportunities below MIN_SCORE are filtered out.
"""

MIN_SCORE = 20

KEYWORDS = {
    # High-value IT / data work
    "ai": 25,
    "artificial intelligence": 25,
    "genai": 25,
    "generative ai": 25,
    "machine learning": 20,
    "llm": 20,
    "data analytics": 20,
    "data platform": 20,
    "data engineering": 20,
    "data science": 18,
    "data warehouse": 15,
    "data lake": 15,
    # Cloud / modern platforms
    "azure": 18,
    "aws": 18,
    "cloud migration": 18,
    "cloud": 12,
    "devops": 15,
    "kubernetes": 12,
    "docker": 10,
    # CRM / enterprise apps
    "salesforce": 25,
    "crm": 20,
    "dynamics 365": 18,
    "dynamics": 15,
    "servicenow": 15,
    "enterprise application": 15,
    # Low/no code
    "low code": 15,
    "no code": 15,
    "power platform": 15,
    "power apps": 15,
    "power automate": 12,
    # Modernization / digital transformation
    "digital transformation": 18,
    "government modernization": 18,
    "modernization": 15,
    "legacy modernization": 18,
    "workflow automation": 15,
    "robotic process automation": 15,
    "rpa": 12,
    # Project / delivery management
    "agile": 12,
    "scrum": 10,
    "pmo": 12,
    "project management": 10,
    "product management": 12,
    "product owner": 10,
    # Case management / citizen services
    "case management": 18,
    "citizen services": 15,
    "human services": 12,
    # IT / software
    "software development": 15,
    "software engineering": 15,
    "it services": 15,
    "information technology": 12,
    "cybersecurity": 12,
    "system integration": 15,
    "api": 10,
}

NEGATIVE_KEYWORDS = [
    "construction", "road", "bridge", "electrical", "hvac",
    "landscaping", "plumbing", "janitorial", "custodial",
    "food service", "cafeteria", "laundry", "printing press",
    "vehicle", "trucking", "freight", "logistics", "security guard",
    "physical security", "facility management",
]

REASONS_THRESHOLD = 10  # only show keyword matches above this score value


def score(opportunity: dict) -> dict:
    text = (
        (opportunity.get("title") or "") + " " +
        (opportunity.get("description") or "")
    ).lower()

    # Immediate reject on negative keywords
    for neg in NEGATIVE_KEYWORDS:
        if neg in text:
            opportunity["score"] = 0
            opportunity["reasons"] = [f"Excluded: contains '{neg}'"]
            return opportunity

    total = 0
    reasons = []
    for keyword, points in KEYWORDS.items():
        if keyword in text:
            total += points
            if points >= REASONS_THRESHOLD:
                reasons.append(f"{keyword.title()} (+{points})")

    opportunity["score"] = min(total, 100)
    opportunity["reasons"] = reasons or ["General IT match"]
    return opportunity


def filter_and_score(opportunities: list) -> list:
    scored = [score(o) for o in opportunities]
    relevant = [o for o in scored if o["score"] >= MIN_SCORE]
    return sorted(relevant, key=lambda x: x["score"], reverse=True)
