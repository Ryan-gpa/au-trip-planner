---
name: trip-research
description: Research and recommend flights, hotels, and ground transport for an Australian domestic business trip, applying a staff member's travel policy tier, with reviews. Trigger with "plan a trip to [city]", "business trip to [city]", "research travel for [dates]", "open trip planner", "trip planner form", or similar.
---

# Trip Research

Research an Australian domestic business trip end-to-end — flights, hotels, and ground transport — the way an experienced executive assistant would: matched to who is actually traveling, not just the cheapest option on the page. Present a reviewed, compared set of options. This skill never books or spends money; it recommends, and a human decides.

## Step 1 — Get the trip details: freeform or form

Two ways in — use whichever fits what the user gave you:

**A. Freeform prompt already has enough detail** (e.g. "Business trip: Sydney to Melbourne for Jane Ngo, Mon 21 July to Wed 23 July, meeting in the CBD") — extract directly and skip to Step 2:
- **Origin** and **destination** city
- **Dates** (departure and return, or a date range)
- **Meeting/business location** at the destination, if mentioned (used to anchor hotel search)
- **Traveler count** (default 1 if not stated)
- **Traveler name or role** (e.g. "Jane Ngo", "the CFO", "a new analyst") — this drives Step 3. If genuinely not given, ask for it before proceeding rather than guessing; who is traveling changes almost every recommendation this skill makes.

**B. Details are missing, or the user explicitly asked to "open trip planner" / "trip planner form" / similar** — render [references/intake-form.html](references/intake-form.html) using the **interactive widget tool** (not a published Artifact) instead of asking a plain-text question. This distinction matters: the form's submit button calls the global `sendPrompt()` function, which only exists inside an interactive widget — publishing this file as a static Artifact instead will render the form but the button will silently do nothing, since `sendPrompt` won't be defined there. The form collects traveler name, origin, destination, both dates, preferred departure time, traveler count, and an optional meeting location, then calls `sendPrompt()` with a constructed sentence — which re-enters the conversation as a new message and triggers this skill again, now with case A's full detail. Prefer the form over a bare text question whenever the user hasn't already committed to typing a freeform sentence — it's faster to fill in than to have a back-and-forth.

Do not assume a default origin city in either path.

## Step 2 — Calendar or email lookup for meeting details (optional, connector-dependent)

Not everyone running this skill has Outlook, Google Calendar, or Gmail connected — treat this exactly like the Duffel/LiteAPI connectors further down: use it if it's there, degrade cleanly if it isn't, never block on it.

1. Check whether a calendar or email tool (Outlook, Google Calendar, Gmail, etc.) is available in the current session's tool list.
2. **If one is available** and the meeting time/location wasn't already given in Step 1: ask the user's permission before touching it — e.g. "I can check your calendar for this meeting's time and location instead of you typing it — want me to?" Only read it after they say yes. Having the tool available doesn't make reading someone's calendar a default action.
3. **If none is available**: don't ask about it more than once per conversation, and don't block the trip request on it. Proceed with whatever the user typed by hand. Add one line in Step 7's close noting that connecting a calendar or email connector would let future requests skip that manual entry — a single suggestion, not a recurring nag.

## Step 3 — Identify the traveler's policy tier

This is the step that separates a real travel desk from a flight-search widget. Everything downstream — cabin class, hotel budget, ground transport, scheduling buffers — depends on who is traveling, not just on price.

1. Look for `settings.local.json` next to this skill (see [README.md](../../README.md) for the format). If it has a `travel_policy.staff` list, match the traveler name/role given in Step 1 against it (case-insensitive, partial match on name is fine — "Jane" matches "Jane Ngo").
2. If matched, use that staff member's `tier`. If a per-person override is present (e.g. a specific `hotel_nightly_cap_aud` or `cabin_class` that differs from their tier default), the override wins.
3. If `settings.local.json` has no `travel_policy` section at all, or the traveler isn't listed, fall back to [references/travel-policy.default.json](references/travel-policy.default.json) and use its `default_tier` ("standard"). State this assumption plainly in the final output (e.g. "No policy match for this traveler — priced at the standard tier") rather than silently defaulting.
4. Never block the flow waiting on tier data — a missing match is a documented default, not a stop condition.

Carry the resolved tier's rules forward into Step 5: `cabin_class`, `cabin_class_min_duration_hours`, `hotel_nightly_cap_aud`, `ground_transport`, `meeting_buffer_minutes`, `avoid_redeye_before_travel_day`, `avoid_early_departure_after_late_arrival`.

## Step 4 — Check for personalization (optional)

Still from `settings.local.json`, layer in anything that isn't tier-specific:

- Default the origin city (still confirm if the prompt already states a different origin)
- Prefer a stated airline or hotel chain when options are otherwise close, and within the resolved tier's cabin class and hotel budget
- Include a Qantas Frequent Flyer or Velocity membership number when checking flight options (see Step 5)

If it's absent, proceed with sensible defaults and no personalization — never require this file.

## Step 5 — Research three legs, filtered by tier

Use live web search/fetch for each leg. Do not fabricate prices, times, or reviews — if a source can't be reached, say so rather than guessing. Apply the tier resolved in Step 3 to every leg below, not just as a note at the end.

### Flights
- Check Google Flights, Skyscanner AU, and Webjet for the route and dates.
- Filter/sort by the tier's `cabin_class`. If `cabin_class_min_duration_hours` is set (e.g. a senior traveler only gets premium economy on sectors 3h+), apply it against the actual flight duration for this route — don't apply a cabin upgrade the policy doesn't call for on a short sector, and don't downgrade a policy-entitled traveler to save money without saying so.
- Apply scheduling buffers: skip options that violate `meeting_buffer_minutes` against a stated meeting time, `avoid_redeye_before_travel_day` (no late-night arrival the night before an early meeting), and `avoid_early_departure_after_late_arrival` (no early-morning outbound the day after a late one, where relevant for multi-leg or return trips).
- Also check Qantas's public Flight Reward Finder for the same route/dates — if a points redemption clearly beats the cash fare, flag it as an alternative (informational only, this skill doesn't book with points).
- Capture per option: airline, cabin, departure/arrival times, price, and any reliability note surfaced in search (e.g. on-time performance).
- If the matched staff profile (Step 3) has a `frequent_flyer` entry for the operating airline, mention it should be added at booking time so status/points accrue correctly — this skill reads it for record keeping and quotes it back to the user, it never submits it anywhere itself.
- If the cheapest available option doesn't meet the traveler's tier (e.g. no business seats left on a preferred route), say so explicitly and present the best policy-compliant option plus the gap, rather than quietly substituting economy.

### Hotels
- Search near the stated meeting location, or the destination CBD if none was given.
- Apply the tier's `hotel_nightly_cap_aud` as a ceiling, not a target — recommend the best-reviewed option within the cap, not automatically the cheapest.
- Capture per option: price/night, star rating, and a short synthesized review summary from Google/TripAdvisor/Booking.com search results — call out points relevant to a business traveler (wifi quality, breakfast included, distance to the meeting location, late checkout).
- If nothing suitable exists under the cap for the dates (e.g. high-demand last-minute booking), say so and present the closest option over cap rather than a poor-fit option that technically fits the number.
- If the matched staff profile has a `hotel_loyalty` entry for the chosen chain, mention it should be added at check-in/booking so points accrue — same rule as frequent flyer numbers: read and quoted back, never submitted anywhere by this skill.

### Ground transport
- Identify the realistic options between the destination airport and the hotel/meeting location: train or airport shuttle service if one exists for that city, taxi rank, rideshare fare estimate, and a car service estimate where relevant.
- Default the recommended option to the tier's `ground_transport` value (`car_service`, `rideshare`, or `public_transit_or_rideshare`) rather than whichever is cheapest, and say why (e.g. "car service booked ahead removes wait-time risk for an executive on a tight connection").
- Capture approximate cost and travel time for each so they're easy to compare.

## Step 6 — Present as a visual Artifact

Build an Artifact (see the Artifact tool) with one section per leg, plus the resolved policy context up top:

- The traveler's name and resolved tier (and a one-line note if it was a default guess, per Step 3.3)
- Each option as a card: price, cabin/rating/reliability note, one-line review highlight, and a small source tag (`web search estimate`, `Duffel`, or `LiteAPI`) so it's clear which numbers are live and which are estimated
- One clearly flagged **recommended pick** per leg, with a one-sentence reason that references the policy where relevant (e.g. "business cabin per executive tier", "under the $250/night cap")
- Any policy exceptions flagged plainly (cheapest option violates tier, nothing fits under the hotel cap, etc.)
- A rough total estimated trip cost combining the recommended picks
- A `sendPrompt()` button on every option card, not just the recommended one — e.g. "Book flight option 2 ↗", "See more hotels near [location] ↗", "Use economy instead ↗". A static card grid with nothing clickable is a rendering bug, not an acceptable output — every card needs at least one action.

## Step 7 — Close clearly

State plainly that these are researched recommendations for the user to book manually. If flight or ride booking has been configured (Duffel / Uber for Business — see README), mention that a booking can be triggered but only ever on an explicit instruction naming the specific option (e.g. "book flight option 2") — never proceed to book without that.

If no calendar/email connector was available in Step 2, add one line suggesting that connecting one (Outlook, Google Calendar) would let future trip requests skip typing the meeting details by hand. Say it once per trip, not every time this skill runs in a session.

## Step 8 — Flight booking and live pricing (optional: Duffel and/or LiteAPI)

Two independent connectors can supply live flight data. Either, both, or neither may be configured — check both, use whatever's available, and **tag every flight option in the Step 6 artifact with its source** (`web search estimate`, `Duffel`, or `LiteAPI`) so it's obvious at a glance where a number came from.

### Duffel
Check for `DUFFEL_ACCESS_TOKEN` (in `.env` next to the repo root, or the environment). If it's not set, skip Duffel entirely.

If it is set, run `python scripts/duffel_flights.py search <ORIGIN_IATA> <DEST_IATA> <depart_date> [<return_date>] [passengers]` to check the token's mode:

- **`duffel_test_...` (sandbox/test mode)**: Duffel's offers here are fictional test data, not real fares — do not use them for the research comparison in Step 5/6, and do not present them as real prices. Their only purpose right now is proving the booking mechanic works safely with zero financial risk. If the user asks to test booking, or asks to book a flight while only a test token is configured, run the search, show the returned test offers clearly labeled "TEST MODE — not a real flight," and only call `python scripts/duffel_flights.py book <offer_id> <given_name> <family_name> <born_on YYYY-MM-DD> <gender M|F> <email> <phone>` after the user explicitly confirms which test offer to "book." State clearly afterward that nothing real was booked.
- **`duffel_live_...` (live mode)**: Duffel's search results are real live fares — tag them `Duffel` and prefer them over web-search estimates for this leg. Never call `book` on a live token without the user explicitly naming the specific offer to book, and always confirm passenger details (full legal name, date of birth, gender, contact info) before booking — get these from the user if not already known, never guess or reuse placeholder data for a real booking.

`book` is never called automatically — only on a follow-up message that explicitly instructs booking a named Duffel option.

### LiteAPI flights
Check for `LITEAPI_SANDBOX_KEY` or `LITEAPI_LIVE_KEY` (same key already used for hotels below). If neither is set, skip.

If a key is set, run `python scripts/liteapi_flights.py search <ORIGIN_IATA> <DEST_IATA> <depart_date> [<return_date>] [adults] [cabin_class]`. Two things to know before relying on it:

- **Flights access is not enabled by default on a LiteAPI key, not even sandbox** — unlike hotels, it has to be requested separately through the LiteAPI dashboard. If the call fails with a 401/403, that means access hasn't been granted yet, not that something is broken — tell the user that plainly and fall back to web-search estimates or Duffel for that leg, rather than retrying or guessing.
- **Booking is not implemented here.** LiteAPI's flight booking currently requires a pre-arranged credit line with them (no card/SDK flow yet per their docs) — that's a commercial arrangement outside what this script can do. Search and price only; if the user asks to book via LiteAPI flights, tell them that's not wired up and explain why, the same way Step 9 handles hotel booking.

When both Duffel and LiteAPI flight data are available for the same route, show both, tagged by source, rather than silently picking one — prices and available fares can differ between them and the user should see that.

## Step 9 — Hotel search and price-lock (optional, requires Nuitee Connect / LiteAPI)

Check for `LITEAPI_SANDBOX_KEY` or `LITEAPI_LIVE_KEY` (in `.env` next to the repo root, or the environment) — the same key as LiteAPI flights above. If neither is set, skip this step — the web-search hotel research from Step 5 is the end of the hotel leg.

If a key is set, run `python scripts/liteapi_hotels.py search <CITY> <COUNTRY_CODE> <checkin> <checkout> [adults] [limit]` and tag these results `LiteAPI` in the artifact — prefer them over the web-search estimates in Step 5/6 for the hotel leg, they're real, live prices and availability, not synthesized from search snippets. Still apply the tier's `hotel_nightly_cap_aud` filter from Step 5 to these results.

**Booking is not available yet, in either sandbox or live mode.** `liteapi_hotels.py` only implements `search` (find rooms) and `prebook` (lock in a rate, returns a `prebookId` — does not charge anything or reserve the room). Completing an actual reservation requires finishing payment through LiteAPI's own hosted payment flow (a browser-based widget, or an Account Credit Card / Wallet configured directly in their dashboard under Payments) — none of which this script can do on its own. If the user asks to book a hotel:

1. Run `search`, then `prebook` on the chosen option — this is safe, locks in the price, and doesn't charge anything.
2. Tell the user plainly that the reservation isn't finished — they need to complete payment on LiteAPI's side (or, once configured, this connector can be extended once we know which payment method they've set up).
3. Never claim a hotel is booked when only `search`/`prebook` have run.
