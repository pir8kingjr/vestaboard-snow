import os, json, requests
from datetime import datetime, timedelta, timezone

# ---------- CONFIG ----------
RW_KEY = os.getenv("VESTABOARD_RW_KEY")  # loaded from GitHub Secrets
RW_URL = "https://rw.vestaboard.com/"
DATA_FILE = "season_totals.json"

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_TZ = "America/Denver"

MT = timezone(timedelta(hours=-7))  # MT for timestamp

LOCATIONS = [
    ("JHMR",     43.585, -110.826),
    ("TARGHEE",  43.789, -110.958),
    ("SNOWBIRD", 40.581, -111.654),
    ("VAIL",     39.606, -106.355),
]

def inches(cm):
    return cm * 0.3937007874

def load_totals():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {name: 0.0 for name, _, _ in LOCATIONS}

def save_totals(totals):
    with open(DATA_FILE, "w") as f:
        json.dump(totals, f, indent=2)

def fetch_season_total(lat, lon):
    start_date = f"{datetime.now().year}-10-01"
    today = datetime.now(timezone.utc).date().isoformat()

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "snowfall_sum",
        "timezone": OPEN_METEO_TZ,
        "start_date": start_date,
        "end_date": today,
    }

    r = requests.get(OPEN_METEO_URL, params=params, timeout=30)
    r.raise_for_status()

    days = r.json().get("daily", {}).get("snowfall_sum", []) or []
    total_cm = sum(v for v in days if isinstance(v, (int, float)))
    return round(inches(total_cm), 1)

def row(label, val):
    vs = f'{val:.1f}"'
    dots = max(1, 22 - len(label) - len(vs))
    return (label + "." * dots + vs)[:22]

def format_board(totals):
    lines = []
    lines.append(" SEASON SNOW TOTALS ".center(22))
    for name, _, _ in LOCATIONS:
        lines.append(row(name, totals.get(name, 0.0)))
    ts = datetime.now(MT).strftime("UPDATED  %b %d %I:%M %p").upper()
    lines.append(ts.center(22))
    return "\n".join(lines)

def post_to_vestaboard(text):
    resp = requests.post(
        RW_URL,
        headers={
            "X-Vestaboard-Read-Write-Key": RW_KEY,
            "Content-Type": "application/json",
        },
        json={"text": text},
        timeout=20
    )
    resp.raise_for_status()

def main():
    old = load_totals()
    new = {}
    for (name, lat, lon) in LOCATIONS:
        try:
            val = fetch_season_total(lat, lon)
            new[name] = max(val, old.get(name, 0.0))  # never decrease
        except Exception:
            new[name] = old.get(name, 0.0)

    save_totals(new)

    payload = format_board(new)
    post_to_vestaboard(payload)

if __name__ == "__main__":
    main()
