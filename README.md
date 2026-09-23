# AU Trip Planner

A Claude Code plugin that researches Australian domestic business trips — flights, hotels, and ground transport — and hands back a reviewed, compared set of options. It never books anything on its own; it recommends, you decide.

## Installation

```bash
claude plugins add au-trip-planner
```

## Usage

Two ways in:

**Type a sentence describing the trip:**

```
Business trip: Melbourne to Brisbane, Mon 21 July to Wed 23 July, meeting in the CBD
```

**Or open the quick-entry form:**

```
Open trip planner
```

This renders a form with Origin, Destination, Depart/Return dates, preferred departure time, traveler count, and an optional meeting location. Submitting it feeds the same skill as the sentence above — pick whichever is faster for you.

Either way, the `trip-research` skill triggers, asks for anything still genuinely missing, and returns a visual comparison covering:

- **Flights** — options from Google Flights, Skyscanner AU, and Webjet, plus a check of whether a Qantas points redemption beats the cash fare
- **Hotels** — options near your meeting location, with a synthesized review summary from Google/TripAdvisor/Booking.com
- **Ground transport** — train/shuttle, taxi, and rideshare estimates between the airport and your hotel

Each leg gets a flagged recommended pick, plus a rough total trip cost.

## Standalone + Supercharged

Works standalone with zero setup. Optionally supercharged with the connectors in [CONNECTORS.md](CONNECTORS.md):

| What You Can Do | Standalone | Supercharged With |
|---|---|---|
| Research flights | Live web search | **Duffel and/or LiteAPI Flights — both built.** Either replaces estimates with real fares, tagged by source in the output so you can see which is which |
| Book a flight | Not available | **Duffel — built.** See setup below. Sandbox by default (fake test bookings, zero risk); switch to a live token when ready to book for real. LiteAPI flight booking is not implemented — it currently requires a pre-arranged credit line with them, not something this repo can set up |
| Research hotels | Live web search | **Nuitee Connect / LiteAPI — search and price-lock built.** See setup below. Real hotel names/prices, not search estimates |
| Book a hotel | Not available | Not yet — LiteAPI's search/prebook works, but completing a reservation needs their payment step finished on their end first (see CONNECTORS.md) |
| Research ground transport | Live web search | State transit open data (Phase 1B) — official real-time data for Sydney/Melbourne/Brisbane |
| Book a ride | Not available | Uber for Business (Phase 3) |

### Setting up Duffel (flight booking)

See [CONNECTORS.md](CONNECTORS.md#duffel-phase-2--setup) for the full walkthrough. Short version:

```bash
cp .env.example .env
# edit .env, set DUFFEL_ACCESS_TOKEN=duffel_test_... (get one at app.duffel.com)
python scripts/duffel_flights.py search SYD MEL 2026-08-01 2026-08-05 1
```

A `duffel_test_` token is sandbox mode — safe to experiment with, no real flights or money involved. The skill only ever books on an explicit "book [option]" instruction, whether in test or live mode.

### Setting up LiteAPI (hotels, and optionally flights)

See [CONNECTORS.md](CONNECTORS.md#nuitee-connect--liteapi-phase-2b--setup) for the full walkthrough. Short version:

```bash
cp .env.example .env
# edit .env, set LITEAPI_SANDBOX_KEY=sand_... (get one at connect.nuitee.com — the SANDBOX KEY under
# Developer tools > API Keys > Private API Keys, not the "Sandbox – Public Key")
python scripts/liteapi_hotels.py search Melbourne AU 2026-08-01 2026-08-05 1
```

Real hotel data, zero cost to search or price-lock (`prebook`). Actually completing a booking isn't wired up yet — see CONNECTORS.md for why.

The same key also covers flights (`scripts/liteapi_flights.py search SYD MEL 2026-08-01 2026-08-05 1`) — but unlike hotels, LiteAPI flight access is off by default even in sandbox. Request it from the LiteAPI dashboard first (Request Assistance → Flights access) or every call will fail with a 401/403. LiteAPI flight booking isn't implemented here either; it currently needs a pre-arranged credit line with them, a commercial step outside this repo.

## Personalization and travel policy

Staff travel profiles live in `settings.local.json` next to the `trip-research` skill, under `travel_policy.staff`. Manage them with `scripts/manage_staff.py` rather than hand-editing the file:

```bash
python scripts/manage_staff.py add --name "Jane Ngo" --role CEO --tier executive \
  --home-city Sydney \
  --ff "Qantas Frequent Flyer:1234567" \
  --hotel "Accor Live Limitless:8811223"

python scripts/manage_staff.py list
python scripts/manage_staff.py show "Jane Ngo"
python scripts/manage_staff.py update --name "Jane Ngo" --tier senior
python scripts/manage_staff.py remove --name "Jane Ngo"
```

Each staff member gets a `tier` — `executive`, `senior`, or `standard` — that drives cabin class, hotel budget cap, ground transport, and scheduling buffers for their trips. The default rules for each tier live in [skills/trip-research/references/travel-policy.default.json](skills/trip-research/references/travel-policy.default.json). Frequent flyer and hotel loyalty numbers are stored per person, purely for record keeping — the skill reads them back and tells you to quote them at booking time, it never submits them anywhere itself (no accounts are touched).

If a traveler isn't listed, or `settings.local.json` doesn't exist at all, the skill defaults to the `standard` tier and says so in its output — it never blocks on missing policy data, but it also never silently guesses at what tier someone should get.

The skill works identically with or without this file — it only ever enhances results, never gates them.

## Scope

- **Australia-domestic only** for now — international trips (currency, visa, a much wider source set) aren't handled.
- **Research and recommend, not autonomous booking** — even once Duffel/Uber for Business are configured, no booking or payment ever happens without an explicit instruction naming the specific option to book.
