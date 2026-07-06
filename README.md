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
| Research flights | Live web search | Duffel live mode (once you're past sandbox) replaces estimates with real fares |
| Book a flight | Not available | **Duffel — built.** See setup below. Sandbox by default (fake test bookings, zero risk); switch to a live token when ready to book for real |
| Research ground transport | Live web search | State transit open data (Phase 1B) — official real-time data for Sydney/Melbourne/Brisbane |
| Book a ride | Not available | Uber for Business (Phase 3) |
| Research hotels | Live web search | — (no realistic booking-API path for individuals/small businesses — see CONNECTORS.md) |

### Setting up Duffel (flight booking)

See [CONNECTORS.md](CONNECTORS.md#duffel-phase-2--setup) for the full walkthrough. Short version:

```bash
cp .env.example .env
# edit .env, set DUFFEL_ACCESS_TOKEN=duffel_test_... (get one at app.duffel.com)
python scripts/duffel_flights.py search SYD MEL 2026-08-01 2026-08-05 1
```

A `duffel_test_` token is sandbox mode — safe to experiment with, no real flights or money involved. The skill only ever books on an explicit "book [option]" instruction, whether in test or live mode.

## Personalization

Create a `settings.local.json` file next to the `trip-research` skill to personalize (all fields optional):

```json
{
  "home_city": "Sydney",
  "preferred_airline": "Qantas",
  "frequent_flyer": {
    "program": "Qantas Frequent Flyer",
    "number": "1234567"
  }
}
```

The skill works identically with or without this file — it only ever enhances results, never gates them.

## Scope

- **Australia-domestic only** for now — international trips (currency, visa, a much wider source set) aren't handled.
- **Research and recommend, not autonomous booking** — even once Duffel/Uber for Business are configured, no booking or payment ever happens without an explicit instruction naming the specific option to book.
