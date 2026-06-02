import requests
import json
import os
from datetime import datetime, timedelta

DATA_FILE = "data/sam_gov.json"
API_BASE = "https://api.sam.gov/opportunities/v2/search"

IT_NAICS = [
    "541511", "541512", "541513", "541519",  # IT services
    "541611", "541618",                        # Management consulting
    "518210",                                  # Data processing / cloud
    "519130",                                  # Web portals
    "561499",                                  # Business support
]


def scrape(api_key: str):
    if not api_key:
        print("[SAM.gov] No API key provided, skipping.")
        return []

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%m/%d/%Y")
    today = datetime.now().strftime("%m/%d/%Y")

    opportunities = []
    for naics in IT_NAICS:
        try:
            params = {
                "api_key": api_key,
                "postedFrom": yesterday,
                "postedTo": today,
                "ncode": naics,
                "limit": 25,
                "offset": 0,
            }
            resp = requests.get(API_BASE, params=params, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                for opp in data.get("opportunitiesData", []):
                    opportunities.append({
                        "title": opp.get("title", ""),
                        "url": opp.get("uiLink", ""),
                        "description": opp.get("description", "")[:500],
                        "naics": naics,
                        "response_date": opp.get("responseDeadLine", ""),
                        "posted_date": opp.get("postedDate", ""),
                        "source": "SAM.gov",
                        "notice_type": opp.get("type", ""),
                    })
        except Exception as e:
            print(f"[SAM.gov] Error for NAICS {naics}: {e}")

    seen = set()
    unique = []
    for o in opportunities:
        if o["url"] not in seen:
            seen.add(o["url"])
            unique.append(o)

    return unique


def get_new(current: list) -> list:
    if not os.path.exists(DATA_FILE):
        return current

    with open(DATA_FILE) as f:
        previous = json.load(f)

    prev_urls = {p["url"] for p in previous}
    return [p for p in current if p["url"] not in prev_urls]


def save(opportunities: list):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(opportunities, f, indent=2)


if __name__ == "__main__":
    key = os.environ.get("SAM_GOV_API_KEY", "")
    current = scrape(key)
    new_items = get_new(current)
    save(current)
    print(json.dumps(new_items, indent=2))
