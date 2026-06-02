import requests
from bs4 import BeautifulSoup
import json
import os

DATA_FILE = "data/subnet.json"
# SBA SUBNet search page — IT/Technology opportunities
URLS = [
    "https://eweb1.sba.gov/subnet/client/dsp_Landing.cfm",
]

def scrape():
    opportunities = []
    try:
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0"})

        # SBA SUBNet main listing
        resp = session.get(
            "https://eweb1.sba.gov/subnet/client/dsp_OpportunityList.cfm",
            timeout=20,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        rows = soup.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                title_cell = cells[0]
                a = title_cell.find("a")
                if not a:
                    continue
                title = a.get_text(strip=True)
                href = a.get("href", "")
                url = href if href.startswith("http") else f"https://eweb1.sba.gov/subnet/client/{href}"
                description = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                response_date = cells[-1].get_text(strip=True) if cells else ""
                opportunities.append({
                    "title": title,
                    "url": url,
                    "description": description,
                    "response_date": response_date,
                    "source": "SBA SUBNet",
                })
    except Exception as e:
        print(f"[SUBNet] Fetch error: {e}")

    return opportunities


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
    current = scrape()
    new_items = get_new(current)
    save(current)
    print(json.dumps(new_items, indent=2))
