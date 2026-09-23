"""
Standalone trip-planner service.

Runs independently of Claude/Cowork — a plain HTTP API (plus a static web
page) that wraps the same connectors the Claude skill uses:
duffel_flights.py, liteapi_flights.py, liteapi_hotels.py, manage_staff.py.

Anyone on the network with the API key can use this from a browser, curl,
or their own frontend — no Claude account, no Outlook, no Cowork required.

Run locally:
    pip install -r server/requirements.txt
    uvicorn server.app:app --reload --port 8000
    open http://localhost:8000

Deploy anywhere that runs Docker (see server/README.md).

Auth: set TRIP_PLANNER_API_KEY in .env. Every request must send it as the
`x-api-key` header. If TRIP_PLANNER_API_KEY is unset, auth is OFF — fine for
a quick local test, never acceptable once this is reachable from the
internet.

Booking endpoints require an explicit "confirm": true in the request body.
That is the only line of defense against an accidental real charge once a
live Duffel token is in play — do not remove it, do not default it to true.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict

from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import duffel_flights  # noqa: E402
import liteapi_flights  # noqa: E402
import liteapi_hotels  # noqa: E402
import manage_staff  # noqa: E402


def _load_dotenv():
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

app = FastAPI(title="AU Trip Planner — standalone service")


def require_api_key(x_api_key: Optional[str] = Header(None)):
    expected = os.environ.get("TRIP_PLANNER_API_KEY")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Missing or invalid x-api-key header")


def _upstream_error(e: SystemExit):
    raise HTTPException(status_code=502, detail=str(e))


@app.get("/health")
def health():
    return {
        "status": "ok",
        "duffel_configured": bool(os.environ.get("DUFFEL_ACCESS_TOKEN")),
        "liteapi_configured": bool(os.environ.get("LITEAPI_SANDBOX_KEY") or os.environ.get("LITEAPI_LIVE_KEY")),
        "auth_enabled": bool(os.environ.get("TRIP_PLANNER_API_KEY")),
    }


@app.get("/flights/search")
def flights_search(
    origin: str,
    destination: str,
    depart: str,
    return_date: Optional[str] = None,
    passengers: int = 1,
    source: str = "duffel",
    cabin_class: str = "ECONOMY",
    x_api_key: Optional[str] = Header(None),
):
    require_api_key(x_api_key)
    
    # Map common city names to IATA codes for flight APIs
    city_to_iata = {
        "sydney": "SYD",
        "melbourne": "MEL",
        "brisbane": "BNE",
        "perth": "PER",
        "adelaide": "ADL",
        "canberra": "CBR",
        "hobart": "HOB",
        "darwin": "DRW",
        "gold coast": "OOL",
        "cairns": "CNS"
    }
    origin = city_to_iata.get(origin.lower(), origin)
    destination = city_to_iata.get(destination.lower(), destination)

    if source == "duffel":
        try:
            out_offers = duffel_flights.search_offers(origin, destination, depart, None, passengers)
            ret_offers = []
            if return_date:
                ret_offers = duffel_flights.search_offers(destination, origin, return_date, None, passengers)
            return {"source": "Duffel", "outbound_offers": out_offers, "return_offers": ret_offers}
        except SystemExit as e:
            _upstream_error(e)
    elif source == "liteapi":
        try:
            out_offers = liteapi_flights.search(origin, destination, depart, None, passengers, cabin_class)
            ret_offers = []
            if return_date:
                ret_offers = liteapi_flights.search(destination, origin, return_date, None, passengers, cabin_class)
            return {"source": "LiteAPI", "outbound_offers": out_offers, "return_offers": ret_offers}
        except SystemExit as e:
            _upstream_error(e)
    else:
        raise HTTPException(status_code=400, detail="source must be 'duffel' or 'liteapi'")


@app.get("/hotels/search")
def hotels_search(
    city: str,
    country: str,
    checkin: str,
    checkout: str,
    adults: int = 1,
    limit: int = 5,
    x_api_key: Optional[str] = Header(None),
):
    require_api_key(x_api_key)
    
    # Map common IATA codes to city names for LiteAPI hotel search
    iata_to_city = {
        "SYD": "Sydney",
        "MEL": "Melbourne",
        "BNE": "Brisbane",
        "PER": "Perth",
        "ADL": "Adelaide",
        "CBR": "Canberra",
        "HOB": "Hobart",
        "DRW": "Darwin",
        "OOL": "Gold Coast",
        "CGC": "Gold Coast",
        "CNS": "Cairns"
    }
    city_name = iata_to_city.get(city.upper(), city)
    
    try:
        return {"source": "LiteAPI", "hotels": liteapi_hotels.search(city_name, country, checkin, checkout, adults, limit)}
    except SystemExit as e:
        _upstream_error(e)


@app.post("/hotels/prebook")
def hotels_prebook(offer_id: str, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    try:
        return liteapi_hotels.prebook(offer_id)
    except SystemExit as e:
        _upstream_error(e)


class BookFlightRequest(BaseModel):
    offer_id: str
    given_name: str
    family_name: str
    born_on: str
    gender: str
    email: str
    phone: str
    confirm: bool = False


@app.post("/flights/book")
def flights_book(req: BookFlightRequest, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    if not req.confirm:
        raise HTTPException(
            status_code=400,
            detail="Set confirm=true to actually book. On a duffel_live_ token this spends real money and cannot be undone by this API.",
        )
    try:
        return duffel_flights.create_order(
            req.offer_id, req.given_name, req.family_name, req.born_on, req.gender, req.email, req.phone
        )
    except SystemExit as e:
        _upstream_error(e)


@app.get("/staff")
def staff_list(x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    settings = manage_staff._load_settings()
    return manage_staff._staff_list(settings)


@app.get("/staff/{name}")
def staff_show(name: str, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    settings = manage_staff._load_settings()
    person = manage_staff._find(manage_staff._staff_list(settings), name)
    if not person:
        raise HTTPException(status_code=404, detail=f"No profile for '{name}'")
    return person


class StaffUpsert(BaseModel):
    name: str
    role: Optional[str] = None
    tier: str
    home_city: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    frequent_flyer: Optional[List[Dict[str, str]]] = None
    hotel_loyalty: Optional[List[Dict[str, str]]] = None
    notes: Optional[str] = None


@app.post("/staff")
def staff_add(req: StaffUpsert, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    if req.tier not in manage_staff.VALID_TIERS:
        raise HTTPException(status_code=400, detail=f"tier must be one of {manage_staff.VALID_TIERS}")
    settings = manage_staff._load_settings()
    staff = manage_staff._staff_list(settings)
    if manage_staff._find(staff, req.name):
        raise HTTPException(status_code=409, detail=f"'{req.name}' already exists")
    person = {"name": req.name, "role": req.role or "", "tier": req.tier}
    if req.home_city:
        person["home_city"] = req.home_city
    if req.email:
        person["email"] = req.email
    if req.phone:
        person["phone"] = req.phone
    if req.frequent_flyer is not None:
        person["frequent_flyer"] = req.frequent_flyer
    if req.hotel_loyalty is not None:
        person["hotel_loyalty"] = req.hotel_loyalty
    if req.notes is not None:
        person["notes"] = req.notes
        
    staff.append(person)
    manage_staff._save_settings(settings)
    return person

@app.put("/staff/{name}")
def staff_update(name: str, req: StaffUpsert, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    if req.tier not in manage_staff.VALID_TIERS:
        raise HTTPException(status_code=400, detail=f"tier must be one of {manage_staff.VALID_TIERS}")
    settings = manage_staff._load_settings()
    staff = manage_staff._staff_list(settings)
    person = manage_staff._find(staff, name)
    if not person:
        raise HTTPException(status_code=404, detail=f"No profile for '{name}'")
    
    person["role"] = req.role or ""
    person["tier"] = req.tier
    if req.home_city is not None:
        person["home_city"] = req.home_city
    if req.email is not None:
        person["email"] = req.email
    if req.phone is not None:
        person["phone"] = req.phone
    if req.frequent_flyer is not None:
        person["frequent_flyer"] = req.frequent_flyer
    if req.hotel_loyalty is not None:
        person["hotel_loyalty"] = req.hotel_loyalty
    if req.notes is not None:
        person["notes"] = req.notes
    manage_staff._save_settings(settings)
    return person

TRIPS_FILE = REPO_ROOT / "trips.json"

def _load_trips():
    if not TRIPS_FILE.exists():
        return []
    import json
    try:
        return json.loads(TRIPS_FILE.read_text())
    except:
        return []

def _save_trips(trips):
    import json
    TRIPS_FILE.write_text(json.dumps(trips, indent=2))

@app.get("/trips")
def get_trips(x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    return _load_trips()

@app.post("/trips")
def add_trip(req: dict, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    trips = _load_trips()
    import uuid, datetime
    req["id"] = str(uuid.uuid4())
    req["created_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    # Pre-calculate GST and totals for the receipt
    total = 0.0
    for item in req.get("items", []):
        total += float(item.get("amount", 0))
    
    # 10% GST means GST is Total / 11
    gst = total / 11.0
    base = total - gst
    
    req["summary"] = {
        "base_amount": round(base, 2),
        "gst_amount": round(gst, 2),
        "total_amount": round(total, 2),
        "currency": "AUD"
    }
    
    trips.insert(0, req) # add to top
    _save_trips(trips)
    return req

@app.get("/calendar/check")
def calendar_check(date: str, dest: str = "MEL", client_name: Optional[str] = None, client_address: Optional[str] = None, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    
    locations = {
        "SYD": "Client HQ: 1 Martin Place, Sydney",
        "MEL": "Client HQ: 100 Collins St, Melbourne",
        "BNE": "Client HQ: 1 William St, Brisbane"
    }
    
    c_name = client_name if client_name else "Client"
    if client_address:
        loc = client_address
    else:
        loc = locations.get(dest.upper(), f"Client Office in {dest.upper()}")

    return {
        "status": "success",
        "mock": True,
        "date": date,
        "events": [
            {
                "subject": f"{c_name} Pitch & Review",
                "start": f"{date}T10:00:00",
                "end": f"{date}T12:00:00",
                "location": loc
            },
            {
                "subject": "Sync with Engineering (Teams)",
                "start": f"{date}T14:00:00",
                "end": f"{date}T15:00:00",
                "location": "Virtual (Teams)"
            }
        ],
        "client_address": loc.replace("Client HQ: ", ""),
        "recommendation": f"Crucial in-person meeting at 10:00 AM at {loc}. Recommend arriving the night before or booking a flight landing before 08:00 AM."
    }


static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
