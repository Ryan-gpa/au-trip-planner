"""
Nuitee Connect (LiteAPI) hotel search and prebook — Phase 2B connector for au-trip-planner.

Zero extra dependencies (stdlib only: urllib). Reads LITEAPI_SANDBOX_KEY (or
LITEAPI_LIVE_KEY) from the environment, or from a .env file next to the repo root.

Usage:
    python liteapi_hotels.py search MELBOURNE AU 2026-07-07 2026-07-11 [adults] [limit]
    python liteapi_hotels.py prebook <offer_id>

NOTE: booking is not wired up yet. Prebook locks in a price and returns a
prebookId, but completing the reservation requires either LiteAPI's browser-based
payment widget or an Account Credit Card / Wallet configured in their dashboard
under Payments — neither of which this script can drive on its own. Do not add
a book() call here until that's resolved; a prebook without a completed booking
holds nothing and charges nothing.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = "https://api.liteapi.travel/v3.0"


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


def _key():
    _load_dotenv()
    key = os.environ.get("LITEAPI_LIVE_KEY") or os.environ.get("LITEAPI_SANDBOX_KEY")
    if not key:
        raise SystemExit(
            "LITEAPI_SANDBOX_KEY is not set. Add it to .env or export it before running this script."
        )
    return key


def _request(method, path, body=None):
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-API-Key", _key())
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8")
        raise SystemExit(f"LiteAPI error {e.code}: {detail}")


def search_hotels(city_name, country_code, limit=20):
    result = _request("GET", f"/data/hotels?countryCode={country_code}&cityName={city_name}&limit={limit}")
    return {h["id"]: h for h in result.get("data", [])}


def search(city_name, country_code, checkin, checkout, adults=1, limit=5):
    hotels_by_id = search_hotels(city_name, country_code, limit=30)

    body = {
        "checkin": checkin,
        "checkout": checkout,
        "currency": "AUD",
        "guestNationality": "AU",
        "cityName": city_name,
        "countryCode": country_code,
        "occupancies": [{"rooms": 1, "adults": adults}],
        "limit": limit,
    }
    result = _request("POST", "/hotels/rates", body)

    parsed = []
    for hotel_rate in result.get("data", [])[:limit]:
        hotel_id = hotel_rate.get("hotelId")
        hotel_info = hotels_by_id.get(hotel_id, {})
        room_types = hotel_rate.get("roomTypes", [])
        if not room_types:
            continue
        room = room_types[0]
        rate = room.get("rates", [{}])[0]
        retail = rate.get("retailRate", {}).get("total", [{}])[0]
        parsed.append({
            "hotel_id": hotel_id,
            "hotel_name": hotel_info.get("name", "(name unavailable)"),
            "address": hotel_info.get("address"),
            "stars": hotel_info.get("stars"),
            "room_name": rate.get("name"),
            "board": rate.get("boardName"),
            "refundable": rate.get("cancellationPolicies", {}).get("refundableTag") != "NRFN",
            "total_price": retail.get("amount"),
            "currency": retail.get("currency"),
            "offer_id": room.get("offerId"),
        })
    return parsed


def prebook(offer_id):
    """Locks in the rate. Does NOT complete a booking or charge anything."""
    result = _request("POST", "/rates/prebook", {"offerId": offer_id, "usePaymentSdk": True})
    data = result["data"]
    return {
        "prebook_id": data["prebookId"],
        "transaction_id": data.get("transactionId"),
        "hotel_id": data.get("hotelId"),
        "currency": data.get("currency"),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "search":
        city, country, checkin, checkout = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
        adults = int(sys.argv[6]) if len(sys.argv) > 6 else 1
        limit = int(sys.argv[7]) if len(sys.argv) > 7 else 5
        print(json.dumps(search(city, country, checkin, checkout, adults, limit), indent=2))
    elif cmd == "prebook":
        print(json.dumps(prebook(sys.argv[2]), indent=2))
    else:
        print(__doc__)
        sys.exit(1)
