# Connectors

This plugin works out of the box with zero setup — Phase 1 (flight/hotel/transport research) uses only Claude's built-in web search and fetch. Everything below is optional, and each row is independent: add as many or as few as you want.

| Category | What it upgrades | Setup | Status |
|---|---|---|---|
| Duffel (flights) | Live flight offers + real booking, gated on your explicit confirmation | Create a Duffel developer account, get a sandbox API key, later a live key + payment method | Not yet built — Phase 2 |
| Uber for Business (ground transport) | Real ride booking, gated on your explicit confirmation | Create a Uber for Business org account and API credentials | Not yet built — Phase 3 |
| State transit open data | Official real-time train/bus/ferry data instead of general web search, for the ground-transport leg | Free self-serve signup, no business verification needed | Not yet built — see table below |

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

**Hotel booking APIs** (Booking.com Connectivity, Expedia Rapid, etc.) are gated behind partner/OTA agreements most individuals and small businesses won't qualify for — hotels stay research-only for the foreseeable future.
