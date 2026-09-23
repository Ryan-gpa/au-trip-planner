# Standalone trip-planner service

A plain HTTP API + web page, independent of Claude, Cowork, Outlook, or anything else. Verified working locally: `/health`, `/staff`, and the frontend all respond correctly with no external network access — the only calls that need real internet are `/flights/search` and `/hotels/search`, which hit Duffel/LiteAPI directly.

## Run it locally right now

```bash
cd au-trip-planner
pip install -r server/requirements.txt
uvicorn server.app:app --reload --port 8000
```

Open `http://localhost:8000` for the web page, or `http://localhost:8000/docs` for the interactive API reference FastAPI generates automatically.

This is the fastest way to prove the Duffel/LiteAPI calls actually work end to end — your machine has normal internet, unlike the Cowork sandbox this was built in.

## Turn on auth before exposing this to the internet

By default, with no `TRIP_PLANNER_API_KEY` set, there is no auth — anyone who can reach the server can search, prebook, and book. Fine for `localhost`, not acceptable anywhere reachable from outside your machine.

Add to `.env`:

```
TRIP_PLANNER_API_KEY=pick-a-long-random-string-here
```

Every request then needs an `x-api-key` header matching it. The web page has a field for this and remembers it in the browser.

## Deploy somewhere it stays online

Any host that runs a Docker container works — Railway, Render, Fly.io, a plain VPS. From the repo root:

```bash
docker build -f server/Dockerfile -t au-trip-planner .
docker run -p 8000:8000 --env-file .env au-trip-planner
```

On a hosting platform, set the same environment variables (`DUFFEL_ACCESS_TOKEN`, `LITEAPI_SANDBOX_KEY` / `LITEAPI_LIVE_KEY`, `TRIP_PLANNER_API_KEY`) in their dashboard rather than shipping `.env` inside the image — `.dockerignore` already excludes it from the build.

## What this does and doesn't fix

Fixes: the service is now online 24/7 wherever you deploy it, callable by anyone with the API key, with no dependency on Outlook, Claude, or a chat session being open.

Doesn't fix: LiteAPI flights access still has to be requested from their dashboard (off by default), LiteAPI hotel booking still stops at prebook (needs their hosted payment step), and Duffel booking on a live token still spends real money the moment `confirm: true` is sent — none of that is a code limitation, it's what those vendors actually support today.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | No auth required check of what's configured |
| GET | `/flights/search` | `origin, destination, depart, return_date?, passengers?, source=duffel\|liteapi, cabin_class?` |
| GET | `/hotels/search` | `city, country, checkin, checkout, adults?, limit?` |
| POST | `/hotels/prebook` | `offer_id` — locks a rate, charges nothing |
| POST | `/flights/book` | Body needs `confirm: true` or it refuses — this is deliberate |
| GET | `/staff` | List staff travel profiles |
| GET | `/staff/{name}` | One profile |
| POST | `/staff` | Add a profile (`name`, `tier`, optional `role`/`home_city`) |
