---
name: trip-research
description: Research and recommend flights, hotels, and ground transport for an Australian domestic business trip, with reviews. Trigger with "plan a trip to [city]", "business trip to [city]", "research travel for [dates]", "open trip planner", "trip planner form", or similar.
---

# Trip Research

Research an Australian domestic business trip end-to-end — flights, hotels, and ground transport — and present a reviewed, compared set of options. This skill never books or spends money; it recommends, and a human decides.

## Step 1 — Get the trip details: freeform or form

Two ways in — use whichever fits what the user gave you:

**A. Freeform prompt already has enough detail** (e.g. "Business trip: Sydney to Melbourne, Mon 21 July to Wed 23 July, meeting in the CBD") — extract directly and skip to Step 2:
- **Origin** and **destination** city
- **Dates** (departure and return, or a date range)
- **Meeting/business location** at the destination, if mentioned (used to anchor hotel search)
- **Traveler count** (default 1 if not stated)

**B. Details are missing, or the user explicitly asked to "open trip planner" / "trip planner form" / similar** — render [references/intake-form.html](references/intake-form.html) using the **interactive widget tool** (not a published Artifact) instead of asking a plain-text question. This distinction matters: the form's submit button calls the global `sendPrompt()` function, which only exists inside an interactive widget — publishing this file as a static Artifact instead will render the form but the button will silently do nothing, since `sendPrompt` won't be defined there. The form collects origin, destination, both dates, preferred departure time, traveler count, and an optional meeting location, then calls `sendPrompt()` with a constructed sentence — which re-enters the conversation as a new message and triggers this skill again, now with case A's full detail. Prefer the form over a bare text question whenever the user hasn't already committed to typing a freeform sentence — it's faster to fill in than to have a back-and-forth.

Do not assume a default origin city in either path.

## Step 2 — Check for personalization (optional)

Look for `settings.local.json` next to this skill (see [README.md](../../README.md) for the format). If present, use it to:

- Default the origin city (still confirm if the prompt already states a different origin)
- Prefer a stated airline or hotel chain when options are otherwise close
- Include a Qantas Frequent Flyer or Velocity membership number when checking flight options (see Step 3)

If it's absent, proceed with sensible defaults and no personalization — never require this file.

## Step 3 — Research three legs

Use live web search/fetch for each leg. Do not fabricate prices, times, or reviews — if a source can't be reached, say so rather than guessing.

### Flights
- Check Google Flights, Skyscanner AU, and Webjet for the route and dates.
- Also check Qantas's public Flight Reward Finder for the same route/dates — if a points redemption clearly beats the cash fare, flag it as an alternative (informational only, this skill doesn't book with points).
- Capture per option: airline, departure/arrival times, price, and any reliability note surfaced in search (e.g. on-time performance).
- If a frequent-flyer number is available from `settings.local.json`, mention it should be added at booking time so status/points accrue correctly — this skill doesn't submit it anywhere itself.

### Hotels
- Search near the stated meeting location, or the destination CBD if none was given.
- Capture per option: price/night, star rating, and a short synthesized review summary from Google/TripAdvisor/Booking.com search results — call out points relevant to a business traveler (wifi quality, breakfast included, distance to the meeting location, late checkout).

### Ground transport
- Identify the realistic options between the destination airport and the hotel/meeting location: train or airport shuttle service if one exists for that city, taxi rank, and a rideshare fare estimate.
- Capture approximate cost and travel time for each so they're easy to compare.

## Step 4 — Present as a visual Artifact

Build an Artifact (see the Artifact tool) with one section per leg:

- Each option as a card: price, rating/reliability note, one-line review highlight
- One clearly flagged **recommended pick** per leg, with a one-sentence reason
- A rough total estimated trip cost combining the recommended picks

## Step 5 — Close clearly

State plainly that these are researched recommendations for the user to book manually. If flight or ride booking has been configured (Duffel / Uber for Business — see README), mention that a booking can be triggered but only ever on an explicit instruction naming the specific option (e.g. "book flight option 2") — never proceed to book without that.

## Step 6 — Flight booking (optional, requires Duffel)

Check for `DUFFEL_ACCESS_TOKEN` (in `.env` next to the repo root, or the environment). If it's not set, skip this step entirely — Step 5's close is the end of the flow.

If it is set, run `python scripts/duffel_flights.py search <ORIGIN_IATA> <DEST_IATA> <depart_date> [<return_date>] [passengers]` to check the token's mode:

- **`duffel_test_...` (sandbox/test mode)**: Duffel's offers here are fictional test data, not real fares — do not use them for the research comparison in Step 3/4, and do not present them as real prices. Their only purpose right now is proving the booking mechanic works safely with zero financial risk. If the user asks to test booking, or asks to book a flight while only a test token is configured, run the search, show the returned test offers clearly labeled "TEST MODE — not a real flight," and only call `python scripts/duffel_flights.py book <offer_id> <given_name> <family_name> <born_on YYYY-MM-DD> <gender M|F> <email> <phone>` after the user explicitly confirms which test offer to "book." State clearly afterward that nothing real was booked.
- **`duffel_live_...` (live mode)**: Duffel's search results are real live fares — at that point, prefer them over the web-search estimates in Step 3 for the flights leg (they're more accurate: real-time pricing and availability straight from the airline). Never call `book` on a live token without the user explicitly naming the specific offer to book, and always confirm passenger details (full legal name, date of birth, gender, contact info) before booking — get these from the user if not already known, never guess or reuse placeholder data for a real booking.

Either way, `book` is never called automatically as part of Step 4/5 — only on a follow-up message that explicitly instructs booking a named option.

## Step 7 — Hotel search and price-lock (optional, requires Nuitee Connect / LiteAPI)

Check for `LITEAPI_SANDBOX_KEY` or `LITEAPI_LIVE_KEY` (in `.env` next to the repo root, or the environment). If neither is set, skip this step — the web-search hotel research from Step 3 is the end of the hotel leg.

If a key is set, run `python scripts/liteapi_hotels.py search <CITY> <COUNTRY_CODE> <checkin> <checkout> [adults] [limit]` and prefer its results over the web-search estimates in Step 3/4 for the hotel leg — they're real, live prices and availability, not synthesized from search snippets.

**Booking is not available yet, in either sandbox or live mode.** `liteapi_hotels.py` only implements `search` (find rooms) and `prebook` (lock in a rate, returns a `prebookId` — does not charge anything or reserve the room). Completing an actual reservation requires finishing payment through LiteAPI's own hosted payment flow (a browser-based widget, or an Account Credit Card / Wallet configured directly in their dashboard under Payments) — none of which this script can do on its own. If the user asks to book a hotel:

1. Run `search`, then `prebook` on the chosen option — this is safe, locks in the price, and doesn't charge anything.
2. Tell the user plainly that the reservation isn't finished — they need to complete payment on LiteAPI's side (or, once configured, this connector can be extended once we know which payment method they've set up).
3. Never claim a hotel is booked when only `search`/`prebook` have run.
