"""
Duffel flight search and booking — Phase 2 connector for au-trip-planner.

Zero extra dependencies (stdlib only: urllib). Reads DUFFEL_ACCESS_TOKEN from
the environment, or from a .env file next to the repo root if present.

Usage:
    python duffel_flights.py search SYD MEL 2026-07-07 [2026-07-11] [passengers]
    python duffel_flights.py book <offer_id> <given_name> <family_name> <born_on> <gender M|F> <email> <phone>

book() is never called automatically — it only runs when explicitly invoked,
matching the plugin's "no booking without an explicit instruction" rule.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = "https://api.duffel.com"
DUFFEL_VERSION = "v2"


def _load_dotenv():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def _token():
    _load_dotenv()
    token = os.environ.get("DUFFEL_ACCESS_TOKEN")
    if not token:
        raise SystemExit(
            "DUFFEL_ACCESS_TOKEN is not set. Add it to .env or export it before running this script."
        )
    return token


def _request(method, path, body=None):
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_token()}")
    req.add_header("Duffel-Version", DUFFEL_VERSION)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8")
        raise SystemExit(f"Duffel API error {e.code}: {detail}")


def search_offers(origin, destination, depart_date, return_date=None, passengers=1):
    slices = [{"origin": origin, "destination": destination, "departure_date": depart_date}]
    if return_date:
        slices.append({"origin": destination, "destination": origin, "departure_date": return_date})

    body = {
        "data": {
            "slices": slices,
            "passengers": [{"type": "adult"} for _ in range(passengers)],
            "cabin_class": "economy",
        }
    }
    result = _request("POST", "/air/offer_requests?return_offers=true", body)
    offers = result.get("data", {}).get("offers", [])

    parsed = []
    for o in offers[:10]:
        slices_out = o.get("slices", [])
        first_slice = slices_out[0] if slices_out else {}
        segments = first_slice.get("segments", [])
        first_seg = segments[0] if segments else {}
        parsed.append({
            "offer_id": o["id"],
            "airline": first_seg.get("marketing_carrier", {}).get("name"),
            "total_amount": o.get("total_amount"),
            "total_currency": o.get("total_currency"),
            "departing_at": first_seg.get("departing_at"),
            "arriving_at": first_seg.get("arriving_at"),
            "expires_at": o.get("expires_at"),
        })
    return parsed


def create_order(offer_id, given_name, family_name, born_on, gender, email, phone_number):
    """Only call this on an explicit user instruction naming the offer to book."""
    offer = _request("GET", f"/air/offers/{offer_id}")
    passenger_id = offer["data"]["passengers"][0]["id"]
    total_amount = offer["data"]["total_amount"]
    total_currency = offer["data"]["total_currency"]

    body = {
        "data": {
            "selected_offers": [offer_id],
            "passengers": [{
                "id": passenger_id,
                "given_name": given_name,
                "family_name": family_name,
                "born_on": born_on,
                "gender": gender,
                "email": email,
                "phone_number": phone_number,
                "title": "mr" if gender == "M" else "mrs",
            }],
            "payments": [{
                "type": "balance",
                "amount": total_amount,
                "currency": total_currency,
            }],
        }
    }
    return _request("POST", "/air/orders", body)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "search":
        origin, destination, depart = sys.argv[2], sys.argv[3], sys.argv[4]
        ret = sys.argv[5] if len(sys.argv) > 5 else None
        pax = int(sys.argv[6]) if len(sys.argv) > 6 else 1
        offers = search_offers(origin, destination, depart, ret, pax)
        print(json.dumps(offers, indent=2))
    elif cmd == "book":
        result = create_order(*sys.argv[2:9])
        print(json.dumps(result, indent=2))
    else:
        print(__doc__)
        sys.exit(1)
