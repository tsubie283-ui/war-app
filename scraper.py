import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.fangraphs.com/leaders/major-league"

def _fetch_war(url):
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")

    data = {}
    rows = soup.select("table tbody tr")

    for row in rows:
        link = row.select_one("a")
        if not link:
            continue

        href = link.get("href", "")
        try:
            player_id = int(href.split("/")[-2])
        except:
            continue

        war_td = row.select("td")[-1]

        try:
            fwar = float(war_td.text.strip())
        except:
            continue

        data[player_id] = fwar

    print(f"FETCHED {len(data)} PLAYERS")

    return data


# 🔵 打者WAR
def fetch_war_leaders_bat():
    url = f"{BASE_URL}?pageitems=2000000000&qual=0&pagenum=1"
    return _fetch_war(url)


# 🔴 投手WAR
def fetch_war_leaders_pit():
    url = f"{BASE_URL}?pageitems=2000000000&qual=0&month=0&pos=all&stats=pit&type=8"
    return _fetch_war(url)