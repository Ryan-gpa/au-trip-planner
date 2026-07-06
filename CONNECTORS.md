# Connectors

This plugin works out of the box with zero setup — Phase 1 (flight/hotel/transport research) uses only Claude's built-in web search and fetch. Everything below is optional, and each row is independent: add as many or as few as you want.

| Category | What it upgrades | Setup | Status |
|---|---|---|---|
| Duffel (flights) | Live flight offers + real booking, gated on your explicit confirmation | See below | **Built — Phase 2** |
| Nuitee Connect / LiteAPI (hotels) | Live hotel search + price-lock (prebook), gated on your explicit confirmation | See below | **Search + prebook built — booking still blocked, see below** |
| Uber for Business (ground transport) | Real ride booking, gated on your explicit confirmation | Create a Uber for Business org account and API credentials | Not yet built — Phase 3 |
| State transit open data | Official real-time train/bus/ferry data instead of general web search, for the ground-transport leg | Free self-serve signup, no business verification needed | Not yet built — see table below |

## Duffel (Phase 2) — setup

1. Create a Duffel account at [duffel.com](https://duffel.com), pick your team/workspace.
2. Go to `https://app.duffel.com/<your-team-id>/test/tokens` (or find "Access tokens" under your workspace's developer/API section — dashboard navigation shifts over time) and create a **test mode** token. It starts with `duffel_test_`.
3. Copy `.env.example` to `.env` in the repo root and set `DUFFEL_ACCESS_TOKEN=duffel_test_...`. `.env` is gitignored — never commit it.
4. That's it — `scripts/duffel_flights.py` picks it up automatically. Test it: `python scripts/duffel_flights.py search SYD MEL 2026-08-01 2026-08-05 1`

**Test mode vs live mode:** a `duffel_test_` token returns fictional sandbox offers — safe to experiment with, but not real fares, and "booking" one doesn't book anything real. When ready to go live, generate a `duffel_live_...` token from the same dashboard (Duffel will ask for a payment method and may require additional verification for live flight booking), and swap it into `.env`. The skill checks the token prefix and adjusts behavior automatically — see `SKILL.md` Step 6.

## Nuitee Connect / LiteAPI (Phase 2B) — setup

1. Create an account at [connect.nuitee.com/register](https://connect.nuitee.com/register/) — free, no card required.
2. In the dashboard, go to **Developer tools → API Keys**. Under "Private API Keys," copy the **Sandbox Key** (starts with `sand_`) — not the "Sandbox – Public Key," which is a different value used for a different auth mode and won't work in the `X-API-Key` header.
3. Add it to `.env`: `LITEAPI_SANDBOX_KEY=sand_...`
4. Test it: `python scripts/liteapi_hotels.py search Melbourne AU 2026-08-01 2026-08-05 1`

**What's actually built:** `search` (real live hotel names, prices, availability) and `prebook` (locks in a rate, returns a `prebookId`, charges nothing). **Booking is not built** — completing a real reservation needs LiteAPI's payment flow finished on their end first (their hosted payment widget, or an Account Credit Card / Wallet set up under their dashboard's **Payments** section), which a server-side script can't drive on its own. Until that's resolved, this connector finds and price-locks rooms but can't finish reserving them.

**Sandbox vs live:** the same official MCP server they host (`https://mcp.liteapi.travel/api/mcp?apiKey=YOUR_API_KEY`) can also be added directly as a Claude connector (Settings → Connectors) — no local script or plugin install required, works from Chat/Cowork/Code alike. That's worth revisiting as the primary integration path once the payment question is sorted, since it removes the "needs Claude Code" limitation entirely.

## State transit open data (Phase 1B)

| State/City | Source | Coverage |
|---|---|---|
| NSW (Sydney) | [Transport for NSW Open Data](https://opendata.transport.nsw.gov.au/) | Train, bus, ferry, light rail, real-time |
| VIC (Melbourne) | [PTV Timetable API](https://www.ptv.vic.gov.au/footer/data-and-reporting/datasets/ptv-timetable-api/) | Train, tram, bus, real-time |
| QLD (Brisbane) | [TransLink Open Data](https://translink.com.au/about-translink/open-data) | Bus, train, ferry, tram (SE Queensland) |

No equivalent has been confirmed for other states/cities (Perth, Adelaide, etc.) — those stay web-search-based regardless of configuration.

## Not integrated — noted as a manual alternative

**Flight Centre / FCM Travel** is a full-service Travel Management Company (a human travel-agent model), not a self-serve API. If you'd rather hand trip logistics to a TMC entirely, that's a manual alternative outside this plugin, not something it connects to.

**Qantas Frequent Flyer / Velocity** don't expose a public API for a member's own points balance or redemption. The only integration point is attaching a frequent-flyer number at Duffel booking time (Phase 2) so fare-class eligibility and accrual are correct.

**Hotel booking APIs** (Booking.com Connectivity, Expedia Rapid, etc.) are still gated behind partner/OTA agreements most individuals and small businesses won't qualify for. This turned out to be incomplete, though — Nuitee Connect / LiteAPI is a newer, self-serve alternative built specifically for AI-agent use cases (see above). Search and price-lock are real and working; full booking is blocked on a payment step, not on account access.
