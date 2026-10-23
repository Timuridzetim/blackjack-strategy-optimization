# CROSS MVP — One trip. One firm budget.

A **runnable**, Docker-ready demonstration of CROSS's core proposition: the user provides a destination, travel dates, traveler count and **hard total trip budget**, and CROSS returns optimized whole-trip itineraries with alternative trade-offs, a transparent cost ledger, travel-day schedule and links to reputable provider search pages.

Matches the original CROSS pitch-deck design: navy, cobalt, sky blue, condensed headlines, and the extracted original CROSS logo.

## Features that actually work

- Freeform English request parsing: e.g. `Plan 5 days from Madrid to Lisbon for 2 people under €700`.
- Editable controls for origin, destination, duration, travelers and firm budget.
- Deterministic budget optimizer that searches combinations of transport, accommodation and paid activities and **never displays an option above the budget**.
- Multiple choices: **Best fit**, **Lowest cost**, **More comfort** (if alternatives exist).
- Itemized trip ledger, mandatory sample fees and a separate cash reserve.
- Day-by-day itinerary with timed activities; adjust the budget and recompute.
- Export machine-readable itinerary to JSON, print-friendly layout.
- Optional OpenAI-compatible API for travel **narrative** only; LLM never invents offer prices.
- Backend serves UI and REST API on the same port; complete Dockerfile and Compose setup.
- Public API schema at `/api/docs`.
- No fake checkout, booking success, affiliate attribution or cashback claim.

## Important: demo inventory versus real prices

**Sample prices are fabricated purely for this runnable product demonstration.** The source tag is `synthetic_catalog` in every API response, and the UI labels the figures **DEMO PRICE PREVIEW**. Links on the 'Booking options' tab open real provider search *homepages*, not offer-specific checkout URLs. Do not advertise sample prices as actual bookable fares. No person pays anything to CROSS in this MVP.

True price integrity requires a supplier contract/authorized API returning offer IDs, time of check, mandatory taxes and fees, exact traveler criteria and a fresh reprice before checkout. See integration plan below.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

Open http://127.0.0.1:8080. Tested with Python 3.11+. Windows users can also run `run_windows.bat` after installing Python; macOS/Linux users can run `./run_unix.sh`.

## Docker / low-cost VPS

```bash
cp .env.example .env   # optional; can skip for full demo functionality
docker compose up --build -d
```

The Compose stack binds to `127.0.0.1:8080` by default for safety. Put HTTPS Caddy/Nginx in front of it. Do not expose without authentication, basic rate limiting and abuse protection. External LLM inference does *not* run on the VPS.

To enable optional LLM narrative:

```dotenv
LLM_API_KEY=your_key_here
LLM_BASE_URL=https://your-openai-compatible-provider.example/v1
LLM_MODEL=your-model-id
```

`/api/describe` uses the configured OpenAI-compatible `/chat/completions` endpoint to summarize a **server-computed** plan. No key means a deterministic local summary; all core functions remain available. Don't commit `.env`.

## API endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/api/health` | Service readiness |
| GET | `/api/config` | Demo capability and supported destinations |
| POST | `/api/parse` | Extract unambiguous request fields from English |
| POST | `/api/plan` | Hard-budget optimized itinerary alternatives |
| POST | `/api/describe` | Optional externally generated natural language summary |
| GET | `/api/docs` | OpenAPI documentation |

Example:

```bash
curl -s http://127.0.0.1:8080/api/plan -H 'Content-Type: application/json' \
  -d '{"origin":"Madrid","destination":"Lisbon","days":5,"travelers":2,"budget":700,"start_date":"2026-12-08"}'
```

## Transition to real supplier inventory

The search catalog is isolated in `app/catalog.py`; the example transport pricing is a synthetic Madrid-based fixture (typing another origin does not trigger genuine repricing). The optimizer in `app/engine.py` works only with structured, server-controlled offer records. Replace the fixtures with eligible supplier adapters, never an LLM's guessed ticket price.

Recommended incremental sequence:

1. **Flights:** Licensed flight shopping API. For an Amadeus implementation, run **Flight Offers Search** then **Flight Offers Price** to revalidate the final total. See https://github.com/amadeus4dev/developer-guides/blob/master/docs/resources/flights.md . Availability varies by carrier and contract.
2. **Stays:** Authorized accommodation inventory provider, with occupancy, nights, local taxes and cancellation details, and provider-specific checkout URL.
3. **Activities:** Approved activities feed with ticket quantities and dates. Hold optional and mandatory costs separately.
4. **Price integrity:** Store source, inventory ID, `checked_at`, number of travelers, included baggage, taxes and mandatory fees. Revalidate at click-out, do not guarantee price until supplier has issued a price lock or confirmed booking.
5. **Attribution:** Add partner-managed affiliate links ONLY under the approved merchant's terms. Some cashback methods need separate permission and reconciliation; budget should not depend on unearned rebates.
6. **Analytics:** Visits → completed plans → clicks → eligible bookings; measure true AI tokens/cost and supplier pricing accuracy. Prefer no PII in logs.

**Important supplier constraints:** Skyscanner's Travel API requires commercial agreement/approval and may be unavailable to small student prototypes; Travelpayouts cached flight data cannot be used as live quotes. Research source links:
- https://www.partners.skyscanner.net/contact/travel-api
- https://github.com/travelpayouts/api-docs/blob/master/source/index.html.md
- https://support.travelpayouts.com/hc/en-us/articles/203955593-What-is-Travelpayouts-and-how-it-works

## Demo for the CROSS pitch deck

1. Open the prefilled Madrid → Lisbon trip, 5 days, 2 people, budget €700.
2. Show the **Best fit** whole-trip composition, full budget circle and day's activities.
3. Switch to **Lowest cost** to show choice and potential savings.
4. Raise budget to €900 or reduce it to €500, click **Build my trip** and show constrained repricing.
5. Show **Day by day** and **Booking options** (with demo notice).
6. Say: "The planner and budget engine are functional. Today's inventory is illustrative; supplier quotes are the next integration."

## Tests

```bash
python -m pytest -q
```

## Project layout

```
app/
  main.py             HTTP API and optional LLM copy integration
  engine.py           deterministic budget optimizer + itinerary generation
  catalog.py          example city/transport/stay/activity fixture data
  static/
    index.html        responsive UI
    styles.css        branding/layout
    app.js            browser interactions
    cross-logo.png    extracted from the user's existing CROSS slide deck
Dockerfile            single small VPS process
...
```

© CROSS prototype, 2026.
