"""
Nuitee Connect (LiteAPI) flight search — Phase 2C connector for au-trip-planner.

Zero extra dependencies (stdlib only: urllib). Reads LITEAPI_SANDBOX_KEY (or
LITEAPI_LIVE_KEY) from the environment, or from a .env file next to the repo
root — the same key already used by liteapi_hotels.py. One LiteAPI account
can cover both flights and hotels; Duffel is no longer required just because
you want live flight prices.

IMPORTANT — unlike Hotels, Flights access is NOT enabled by default on a
LiteAPI account, not even in sandbox. You have to request it first from the
LiteAPI dashboard (Request Assistance -> ask for Flights sandbox/production
access). Until that's approved, every call here will fail with an
authorization or "not enabled" error from the API — that is expected, not a
bug in this script.

Booking is not implemented here. As of writing, LiteAPI's flight booking
only supports payment via a pre-arranged credit line (no SDK/card flow yet,
per their docs), which is a commercial arrangement, not something this
script can set up on its own. Search/pricing only, same spirit as
liteapi_hotels.py stopping at prebook.

Usage:
    python liteapi_flights.py search SYD MEL 2026-07-07 [2026-07-11] [adults] [cabin_class]

    cabin_class (optional): ECONOMY | PREMIUM_ECONOMY | BUSINESS | FIRST
    (defaults to ECONOMY)
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


def _request(body):
    req = urllib.request.Request(
        f"{API_BASE}/flights/rates",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
    )
    req.add_header("X-API-Key", _key())
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8")
        if e.code in (401, 403):
            raise SystemExit(
                f"LiteAPI Flights error {e.code}: {detail}\n"
                "Flights access is not enabled by default on a LiteAPI key — "
                "request Flights sandbox/production access from the LiteAPI dashboard first."
            )
        raise SystemExit(f"LiteAPI Flights error {e.code}: {detail}")


def search(origin, destination, depart_date, return_date=None, adults=1, cabin_class="ECONOMY"):
    legs = [{"origin": origin, "destination": destination, "date": depart_date, "direction": "OUTBOUND"}]
    if return_date:
        legs.append({"origin": destination, "destination": origin, "date": return_date, "direction": "INBOUND"})

    body = {
        "legs": legs,
        "adults": adults,
        "currency": "AUD",
        "cabinClass": cabin_class,
    }
    result = _request(body)
    offers = result.get("data", result.get("offers", []))

    parsed = []
    for o in offers[:10]:
        best_sort = o.get("sortMetadata", {}).get("best", {})
        journeys = o.get("journeys", [])
        provider = None
        dep_at = None
        arr_at = None
        ret_dep_at = None
        ret_arr_at = None

        if journeys and journeys[0].get("segments"):
            out_segs = journeys[0]["segments"]
            provider = out_segs[0].get("carrier", {}).get("marketingName")
            dep_at = out_segs[0].get("departure", {}).get("date")
            arr_at = out_segs[-1].get("arrival", {}).get("date")

        if len(journeys) > 1 and journeys[1].get("segments"):
            ret_segs = journeys[1]["segments"]
            ret_dep_at = ret_segs[0].get("departure", {}).get("date")
            ret_arr_at = ret_segs[-1].get("arrival", {}).get("date")

        parsed.append({
            "source": "LiteAPI",
            "offer_id": best_sort.get("offerId") or o.get("id") or o.get("offerId"),
            "provider": provider or o.get("provider") or o.get("validatingCarrier"),
            "total_amount": best_sort.get("price") or o.get("price", {}).get("total") or o.get("totalAmount") or o.get("pricing", {}).get("display", {}).get("total"),
            "currency": best_sort.get("currency") or o.get("price", {}).get("currency") or o.get("currency", "AUD") or o.get("pricing", {}).get("display", {}).get("currency"),
            "cabin_class": cabin_class,
            "departing_at": dep_at,
            "arriving_at": arr_at,
            "return_departing_at": ret_dep_at,
            "return_arriving_at": ret_arr_at,
            "raw": o,
        })
    return parsed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "search":
        origin, destination, depart = sys.argv[2], sys.argv[3], sys.argv[4]
        ret = sys.argv[5] if len(sys.argv) > 5 and not sys.argv[5].isdigit() else None
        remaining = sys.argv[5:] if ret is None else sys.argv[6:]
        adults = int(remaining[0]) if len(remaining) > 0 else 1
        cabin = remaining[1] if len(remaining) > 1 else "ECONOMY"
        print(json.dumps(search(origin, destination, depart, ret, adults, cabin), indent=2))
    else:
        print(__doc__)
        sys.exit(1)
