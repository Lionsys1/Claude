import requests
from bs4 import BeautifulSoup
import json
import os

DATA_FILE = "data/fedtech.json"
URL = "https://fedtech.io/programs"

def scrape():
    try:
        resp = requests.get(URL, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception as e:
        print(f"[FedTech] Fetch error: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    programs = []

    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        href = a["href"]
        if not title or len(title) < 8:
            continue
        if "/programs/" in href or "program" in href.lower():
            url = href if href.startswith("http") else f"https://fedtech.io{href}"
            programs.append({"title": title, "url": url, "source": "FedTech"})

    seen = set()
    unique = []
    for p in programs:
        key = p["url"]
        if key not in seen:
            seen.add(key)
            unique.append(p)

    return unique


def get_new(current: list) -> list:
    if not os.path.exists(DATA_FILE):
        return current

    with open(DATA_FILE) as f:
        previous = json.load(f)

    prev_urls = {p["url"] for p in previous}
    return [p for p in current if p["url"] not in prev_urls]


def save(programs: list):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(programs, f, indent=2)


if __name__ == "__main__":
    current = scrape()
    new_items = get_new(current)
    save(current)
    print(json.dumps(new_items, indent=2))
