# ReliefChain AI: Spec-Driven Build Sheet 
---

## 1. One-line pitch

**ReliefChain AI tracks every individual emergency request from "received" to "verified delivered", and shows in real time which requests are stalled, who owns them, and who was escalated.**

Hackathon track: **Climate, Resource Infrastructure & Global Supply Resilience** (floods, heatwaves, power shortages, supply disruptions).

Core question the product answers: **"Which emergency request is still unresolved right now, and whose job is it?"**

This is NOT a flood map or a generic dashboard. The unit of the product is the **request lifecycle**.

---

## 2. Problem

Climate events (floods, heatwaves, cyclones, power cuts) create demand spikes for water, food, medicine, boats, generators, shelter and transport. Dashboards show affected areas, but individual requests are lost, duplicated, or stall because:
- Requests arrive via calls, WhatsApp, social media, helplines in mixed languages (Tamil, Hindi, English).
- Nobody has a live view of which agency holds which resource.
- Ownership of a request is unclear, so nobody follows up.
- "Delivered" is never verified.

## 3. Goals and non-goals

### Goals (must ship)
1. Ingest messy requests, extract structured data, deduplicate.
2. Maintain a resource registry (agencies, stock, vehicles).
3. Match requests to resources with a real optimizer, respecting constraints.
4. Run a request state machine with SLA timers.
5. Detect gaps: unmatched, matched-but-undispatched, dispatched-but-late, delivered-but-unverified.
6. Escalate automatically along an authority chain with an audit log.
7. Verify delivery through requester confirmation.
8. Anticipatory mode: use a forecast to pre-position resources before an event.
9. A live demo with a replayable simulated flood scenario and measurable metrics.

### Non-goals
- No real WhatsApp/SMS integration required (build a simulator with the same interface and a clearly marked adapter for real providers).
- No national-scale infrastructure. One district / city ward map is enough.
- No autonomous life-critical decisions without a human override path.

---

## 4. Personas

| Persona | Need |
|---|---|
| Citizen / requester | Ask for help in any language, get status, confirm receipt |
| Volunteer / driver | See assigned tasks on a phone, update status, upload proof |
| Agency / NGO coordinator | Publish stock, accept or reject matches |
| District control room officer | See stalled requests, override priority, receive escalations |
| Judge / evaluator | Understand the value in under 2 minutes |

---

## 5. Tech stack (pin these so the build is predictable)

- **Backend:** Python 3.11, FastAPI, SQLModel (SQLAlchemy), SQLite for dev (Postgres-compatible schema), APScheduler for timers.
- **Optimization:** `ortools` (fallback to a greedy matcher if import fails).
- **AI layer:** a single `LLMClient` interface with two implementations:
  - `MockLLM` (rule-based extractor with keyword and regex, works offline, deterministic, used in tests and as fallback)
  - `RealLLM` (uses an env-configured API key; structured JSON output; used only if the key is present)
- **Embeddings / dedupe:** `sentence-transformers` multilingual model if available, else TF-IDF + geo-distance fallback.
- **Frontend:** Next.js (or Vite + React) + TypeScript, Tailwind, MapLibre GL (OpenStreetMap tiles), Recharts.
- **Realtime:** Server-Sent Events from backend to dashboard.
- **Packaging:** `docker-compose.yml` with `api`, `web`; one command to start: `make demo`.
- **Tests:** pytest for backend, Playwright smoke test for the demo flow.

All external services must degrade gracefully. **The demo must run fully offline with no API keys.**

---

## 6. Repository layout

```
reliefchain/
  README.md
  DECISIONS.md
  Makefile
  docker-compose.yml
  .env.example
  backend/
    app/
      main.py
      config.py
      db.py
      models.py            # SQLModel tables
      schemas.py           # Pydantic I/O
      state_machine.py     # allowed transitions + guards
      services/
        intake.py          # parse -> structured request
        dedupe.py
        registry.py
        matching.py        # OR-Tools + greedy fallback
        gaps.py            # gap detector
        escalation.py      # policy engine + audit log
        verification.py
        forecast.py        # anticipatory mode
        scoring.py         # priority scoring
        sse.py
      ai/
        llm_base.py
        mock_llm.py
        real_llm.py
        prompts.py
      adapters/
        channel_base.py    # inbound/outbound message interface
        sim_whatsapp.py    # simulator
        sms_stub.py
      scheduler.py
      api/
        requests.py
        resources.py
        agencies.py
        escalations.py
        sim.py
        metrics.py
    data/
      synthetic/           # generator + seed output
      geo/                 # wards.geojson, road graph (small)
    tests/
  web/
    app/ (pages: control-room, request/[id], volunteer, agency, simulator, impact)
    components/
  scripts/
    generate_synthetic.py
    run_scenario.py
```

---

## 7. Data model

Use UUID primary keys, UTC timestamps. Add `created_at`, `updated_at` to every table.

**Request**
- `id`, `source_channel` (whatsapp|sms|call|social|volunteer|web)
- `raw_text`, `language` (ta|hi|en|other), `translated_text`
- `need_type` enum: WATER, FOOD, MEDICINE, SHELTER, RESCUE_BOAT, MEDICAL_TRANSPORT, GENERATOR, POWER_BACKUP, COOLING, BLANKETS, FUEL, OTHER
- `quantity`, `unit`
- `lat`, `lng`, `ward_id`, `address_text`, `location_confidence` (0-1)
- `urgency` enum: CRITICAL, HIGH, MEDIUM, LOW
- `vulnerability_flags` (JSON list: elderly, disabled, infant, pregnant, bedridden, oxygen_dependent)
- `priority_score` (float)
- `status` (see state machine)
- `duplicate_of` (nullable FK)
- `trust_score` (0-1), `verified_requester` (bool)
- `owner_type`, `owner_id` (who is currently responsible)
- `sla_due_at`, `last_progress_at`
- `escalation_level` (int)

**Agency**: `id`, `name`, `type` (govt|ngo|volunteer_group|private), `contact`, `ward_coverage`, `authority_level`, `parent_agency_id` (for escalation chain)

**Resource**: `id`, `agency_id`, `type` (matches need_type), `quantity_total`, `quantity_available`, `unit`, `lat`, `lng`, `vehicle_capacity` (nullable), `mobility` (static|vehicle), `status`, `last_updated_at`

**Match**: `id`, `request_id`, `resource_id`, `quantity_allocated`, `eta_minutes`, `route_polyline`, `score`, `state` (PROPOSED|ACCEPTED|REJECTED|DISPATCHED|COMPLETED|EXPIRED), `proposed_at`, `accepted_at`

**StatusEvent** (append-only audit): `id`, `request_id`, `from_status`, `to_status`, `actor_type`, `actor_id`, `reason`, `payload`, `timestamp`

**Escalation**: `id`, `request_id`, `level`, `reason_code`, `notified_party_id`, `channel`, `message`, `acknowledged_at`, `timestamp`

**Verification**: `id`, `request_id`, `method` (requester_reply|photo|volunteer_checkin|agency_confirm), `result` (CONFIRMED|DISPUTED|NO_RESPONSE), `evidence_url`, `timestamp`

**RoadSegment** (small graph): `id`, `from_node`, `to_node`, `length_m`, `flooded` (bool), `passable_for` (JSON: car, truck, boat, foot), `updated_at`

**ForecastCell**: `ward_id`, `hazard` (flood|heat|power), `risk` (0-1), `horizon_hours`, `predicted_demand` (JSON by need_type), `generated_at`

---

## 8. Request state machine

States and allowed transitions (enforce in `state_machine.py`; reject anything else with 409):

```
RECEIVED -> TRIAGED -> MATCHED -> ACCEPTED -> DISPATCHED -> DELIVERED -> VERIFIED
                |           |         |            |            |
                |           |         |            |            +-> DISPUTED -> TRIAGED (re-open)
                |           |         +-> REJECTED -> TRIAGED
                +-> UNMATCHABLE (no resource in range) -> ESCALATED
Any non-terminal state -> ESCALATED (via gap detector) -> returns to previous state when acted on
RECEIVED -> DUPLICATE (terminal, links to canonical request)
Any non-terminal -> CANCELLED (requester or officer)
```

Terminal: VERIFIED, DUPLICATE, CANCELLED.

**SLA timers (configurable in `config.py`, defaults in minutes):**

| Urgency | Triage | Match | Accept | Dispatch | Deliver | Verify |
|---|---|---|---|---|---|---|
| CRITICAL | 2 | 5 | 5 | 10 | 45 | 30 |
| HIGH | 5 | 15 | 15 | 30 | 120 | 60 |
| MEDIUM | 15 | 45 | 30 | 90 | 360 | 180 |
| LOW | 60 | 180 | 120 | 240 | 720 | 480 |

For the demo, support a **time-compression factor** (e.g. 1 simulated hour = 10 real seconds) via `SIM_SPEED`.

---

## 9. Core services: behavior spec

### 9.1 Intake (`intake.py`)
Input: raw message + channel metadata. Output: structured Request.
- Detect language; translate to English for processing while keeping original.
- Extract: need_type, quantity, urgency, location text, vulnerability flags, requester contact.
- Geocode location text against a local gazetteer (ward names, landmarks, street list in `data/geo`). If confidence < 0.5, set status to RECEIVED and ask a clarifying question through the channel adapter ("Please share your location pin or nearest landmark").
- LLM must return **strict JSON** validated by Pydantic. On invalid JSON, retry once, then fall back to `MockLLM`.
- Never invent a location or quantity. Unknown fields stay null with a low confidence flag.

### 9.2 Trust and dedupe (`dedupe.py`)
- Candidate duplicates: same need_type, within 300 m, within 6 hours, text similarity > threshold (embedding cosine or TF-IDF).
- Merge by setting `duplicate_of`; increment a `corroboration_count` on the canonical request. **Corroboration raises trust_score.**
- Trust score inputs: verified phone, geo-match between pin and text, number of independent corroborating requests, requester history, spam heuristics. Low-trust CRITICAL requests are routed to a human review queue, never silently dropped.

### 9.3 Priority scoring (`scoring.py`)
`priority = w1*urgency + w2*vulnerability + w3*waiting_time + w4*hazard_risk_at_location + w5*corroboration - w6*duplicate_penalty`
Weights in config. Officers can override with a required reason (logged).

### 9.4 Resource registry (`registry.py`)
- CRUD for agencies and resources; stock updates via API, a simple web form, or simulated WhatsApp message ("Chennai Fire Dept: 3 boats available at Velachery").
- Stock decrements atomically on ACCEPTED match; restored on REJECTED/EXPIRED.
- Staleness: resources not updated within a configurable window are flagged `STALE` and down-weighted in matching.

### 9.5 Matching (`matching.py`)
Formulate as an assignment problem with OR-Tools (CP-SAT or MIP):
- Decision variables: allocate quantity from resource r to request q.
- Hard constraints: stock availability, resource type = need type, road passability for the resource's mobility mode, vehicle capacity, agency coverage area (soft if CRITICAL).
- Objective: maximize priority-weighted fulfillment, minimize ETA, penalize stale resources, penalize splitting a single request across too many sources.
- Support **partial fulfillment**: if a request needs 200 water bottles and only 120 are available, allocate 120 and mark remaining as an **open gap** (see 9.6).
- Re-run matching on triggers: new request, new/updated resource, road status change, match rejection, SLA breach. Must complete in under 3 seconds for 500 requests / 100 resources.
- Provide an **explanation** string per match ("Chosen because nearest boat, passable via Road X, agency covers ward 12").
- Greedy fallback if OR-Tools is unavailable; same interface.

### 9.6 Gap detector (`gaps.py`), the core novelty
Runs every N seconds. Produces `Gap` records (computed view, not necessarily a table) of these types:
1. `NO_RESOURCE_IN_RANGE`: no feasible match (include nearest feasible resource type/distance and **what is missing**).
2. `PARTIAL_FULFILLMENT`: remaining quantity unmatched.
3. `MATCHED_NOT_ACCEPTED`: agency has not accepted within SLA.
4. `ACCEPTED_NOT_DISPATCHED`
5. `DISPATCHED_LATE`: ETA exceeded, no location/status update.
6. `DELIVERED_UNVERIFIED`
7. `NO_OWNER`: request with no responsible party.
8. `ROUTE_BLOCKED`: road status change invalidated an active dispatch.

Each gap carries: request_id, gap_type, severity, age, responsible party, recommended action.

**Aggregate "unmet need" view:** total unmet quantity per need_type per ward. This is the "what supply is missing" output that supports procurement and pre-positioning.

### 9.7 Escalation (`escalation.py`)
Policy engine driven by a YAML file `escalation_policy.yaml`:
```yaml
CRITICAL:
  - after_sla_breach_minutes: 0   -> notify: agency_coordinator
  - after_sla_breach_minutes: 10  -> notify: district_control_room
  - after_sla_breach_minutes: 25  -> notify: collector_office
HIGH: ...
```
- Walk the agency `parent_agency_id` chain; fall back to ward-level authority.
- Each escalation: record to `Escalation`, push to dashboard via SSE, send via channel adapter, require **acknowledgement**; if unacknowledged within X minutes, escalate one level up.
- Escalations **auto-reassign** the request to a new resource when an alternative exists (re-run matching excluding the stalled resource).
- Everything immutable in an audit trail ("who was told, when, what they did").

### 9.8 Verification (`verification.py`)
- On DELIVERED, send requester a confirmation prompt through the channel ("Did you receive 50 water bottles? Reply 1 = Yes, 2 = No / partial").
- Accept photo or volunteer check-in as alternative evidence.
- No response within window: mark `NO_RESPONSE`, trigger a volunteer spot-check task; do not silently mark VERIFIED.
- DISPUTED reopens the request with high priority and increments `escalation_level`.
- Compute a **delivery integrity rate**: verified / delivered.

### 9.9 Anticipatory mode (`forecast.py`)
- Input: rainfall / heat forecast per ward (support loading a JSON/CSV; optional fetch from Open-Meteo or IMD-like source when network is available), static vulnerability layer (elevation, population density, elderly share, past flood history).
- Output: `ForecastCell` risk and predicted demand per need_type per ward for 6/24/48 h horizons. Use a transparent model (gradient boosting or even calibrated heuristics) and **show feature contributions** in the UI. Document the model honestly.
- **Pre-positioning recommendations:** compare predicted demand to registered supply; output "Ward 12 will likely need ~400 water units and 3 boats; registered supply covers 60%. Pre-position from Agency A." This closes the loop between prediction and the request lifecycle.
- Optional satellite flood-extent input: accept a precomputed GeoJSON flood polygon (e.g., from Sentinel-1) and mark road segments inside it as impassable.

### 9.10 Channel adapters (`adapters/`)
Common interface: `receive(message)`, `send(to, text, buttons?)`. Provide:
- `sim_whatsapp`: in-app chat simulator in the web UI, supports Tamil/Hindi/English text, location pin, photo.
- `sms_stub`: logs messages; keyword-based replies ("1"/"2").
- Clear TODO hooks for Twilio / WhatsApp Cloud API.

---

## 10. API contract (REST, JSON; document with OpenAPI automatically)

```
POST   /api/requests/ingest              {channel, raw_text, sender, lat?, lng?, media?}
GET    /api/requests?status=&ward=&urgency=&gap=
GET    /api/requests/{id}                full lifecycle: events, matches, escalations, verification
POST   /api/requests/{id}/override       {priority|owner|status, reason}   (officer)
POST   /api/requests/{id}/cancel

POST   /api/resources                    create
PATCH  /api/resources/{id}               update stock/location
GET    /api/resources?type=&ward=

POST   /api/matches/{id}/accept          (agency)
POST   /api/matches/{id}/reject          {reason}
POST   /api/matches/{id}/dispatch
POST   /api/matches/{id}/deliver         {evidence?}
POST   /api/requests/{id}/verify         {method, result, evidence?}

GET    /api/gaps                         current gaps, filter by type/ward/severity
GET    /api/unmet-need                   aggregated shortages per need/ward
GET    /api/escalations
POST   /api/escalations/{id}/ack

GET    /api/forecast?ward=&hazard=&horizon=
GET    /api/prepositioning               recommendations

POST   /api/roads/{id}/status            {flooded: bool}
POST   /api/sim/start                    {scenario, speed}
POST   /api/sim/stop
POST   /api/sim/inject                   {event: road_block|stock_drop|surge, ...}
GET    /api/metrics                      impact metrics
GET    /api/stream                       SSE: request_update, gap_opened, escalation, match, metric
```

All mutating endpoints write a `StatusEvent`. All responses use consistent error envelopes.

---

## 11. Frontend spec

### Pages
1. **Control Room** (default, the "wow" screen)
   - Left: **"Unresolved Right Now"** list sorted by priority, each with a colored lifecycle stepper (Received > Matched > Accepted > Dispatched > Delivered > Verified), age, owner, gap badge.
   - Center: map with request pins (colored by stage), resources, flooded roads, ward risk overlay, dispatch routes. Clicking a pin opens the request.
   - Right: live **escalation feed** and **unmet-need counter by category**.
   - Top bar: KPIs (open, stalled, avg time-to-match, verified rate) and a **sim clock**.
2. **Request Detail**: full timeline (audit trail), match explanation, who was notified and when, verification status, officer override with reason.
3. **Volunteer view** (mobile-first): assigned tasks, big buttons (Accept / On the way / Delivered), photo upload, works with poor connectivity (queue actions locally, sync later).
4. **Agency portal**: publish stock, accept/reject proposed matches, see capacity.
5. **Simulator**: chat window posting messages as a citizen (multi-language), scenario controls (start flood, block a road, drop stock, surge demand), speed slider.
6. **Impact page**: before vs after comparison (see Section 13), unmet-need breakdown, forecast vs actual.
7. **Pre-positioning page**: forecast risk by ward, predicted demand vs supply, recommended moves.

### UX requirements
- Every request card answers in 1 second: **status, owner, how long stuck, what's next**.
- Color-blind-safe palette, large touch targets, English/Tamil/Hindi UI toggle (at minimum labels for citizen and volunteer views).
- Accessible: keyboard navigation, aria labels, contrast AA.
- Empty/loading/error states for every view.

---

## 12. Synthetic data and the demo scenario (critical for winning)

`scripts/generate_synthetic.py` must create, deterministically (seeded):
- A Chennai-like district: ~15 wards with GeoJSON polygons (can be stylized), elevation index, population, elderly share.
- ~12 agencies (fire dept, municipal corporation, NDRF-like team, 4 NGOs, volunteer groups, a hospital network) with a parent chain up to a district control room and collector office.
- ~100 resources (boats, trucks, generators, water tankers, medicine kits, shelters) with realistic quantities.
- A small road graph with flood-prone segments.
- ~500 citizen requests in mixed Tamil/Hindi/English with typos, code-mixing, duplicates, vague locations, and 5% spam/fakes. Include at least 30 hand-written realistic examples, including:
  - "Appa ku oxygen cylinder venum, Velachery 2nd main road, tanni vandhuduchi" (Tamil-English mix)
  - "Water level rising, 6 people on terrace, one is bedridden, near Tambaram bus stand"
- Pre-baked forecast (rainfall) and a flood-extent polygon.

### Scenario script `run_scenario.py` (3 to 5 minutes at compressed time)
1. T0: Forecast warning. Pre-positioning recommendations shown; some resources moved.
2. T+1: Flood hits; request surge floods in (100+ in two minutes). Dedupe collapses duplicates visibly.
3. T+2: Matching assigns most requests; map lights up.
4. T+3: **Injected failure A:** a key road floods; a dispatched truck's route is invalidated; ReliefChain reroutes and flags `ROUTE_BLOCKED`.
5. T+4: **Injected failure B:** an agency never accepts a CRITICAL match; gap detector flags it; escalation goes to district control room; request is auto-reassigned.
6. T+5: **Unmet need:** boats run out in one ward; system shows "Ward 9 short by 2 boats and 300 water units" and recommends sourcing.
7. T+6: Delivery verification: a requester replies "2 = partial"; request reopens.
8. Final: Impact page shows the numbers.

The scenario must be reproducible with one command and the same seed.

---

## 13. Metrics and baseline comparison (how to "prove" value)

Implement a **baseline simulation** (no ReliefChain: requests handled FIFO by agency-local queues, no cross-agency matching, no gap detection, no verification) and run the same scenario against it. Show side by side:

| Metric | Baseline | ReliefChain |
|---|---|---|
| Median time-to-match | | |
| Requests silently stalled > SLA | | |
| % requests closed AND verified | | |
| Duplicate requests collapsed | | |
| Critical requests handled in SLA | | |
| Unmet need identified per ward | n/a | |
| Delivery integrity rate | n/a | |

Label clearly that these come from a **simulation with synthetic data**; do not claim real-world outcomes. Honesty wins credibility with judges.

---

## 14. Build order (milestones)

**M1: Foundation (backend skeleton)**: models, DB, seed data generator, state machine with tests, status-event audit trail.
**M2: Intake**: MockLLM extractor, optional RealLLM, geocoder with gazetteer, ingest endpoint, dedupe, trust and priority scoring.
**M3: Registry and matching**: resource CRUD, OR-Tools matcher with greedy fallback, explanations, partial fulfillment.
**M4: Lifecycle actions**: accept/reject/dispatch/deliver endpoints, SLA timers, scheduler with sim speed.
**M5: Gap detector and unmet-need view.**
**M6: Escalation engine**: YAML policy, chain walking, acknowledgements, auto-reassign, audit log.
**M7: Verification flow** and integrity rate.
**M8: SSE stream and frontend Control Room** (list + map + feed + KPIs).
**M9: Request Detail, Volunteer view, Agency portal, Simulator page.**
**M10: Forecast + pre-positioning**, road/flood overlay.
**M11: Scenario runner, baseline simulation, Impact page.**
**M12: Polish**: README, one-command demo, error states, accessibility pass, demo script, screenshots, 90-second video script.

Priority if time runs short: M1 to M8 plus M11 give a complete, winning demo. M10 is the next most valuable differentiator.

## Multi-Agent Intelligence Architecture (Mandatory)

ReliefChain AI must be implemented as a genuine multi-agent
system using LangGraph.

### Required Agents

1. Citizen Intake Agent
   - Understand multilingual emergency messages.
   - Extract structured requests.
   - Ask clarification questions when information is missing.

2. Request Verification Agent
   - Identify duplicates.
   - Evaluate request confidence.
   - Flag suspicious requests for human review.

3. Disaster Intelligence Agent
   - Analyse weather forecasts and hazard information.
   - Assess location-specific risk.
   - Recommend urgency levels.

4. Resource Allocation Agent
   - Identify suitable resources.
   - Call the OR-Tools optimization service.
   - Explain allocation decisions.

5. Logistics Agent
   - Calculate feasible delivery routes.
   - Monitor dispatch progress.
   - Recommend alternatives when routes become blocked.

6. Gap Detection Agent
   - Identify unresolved requests.
   - Detect missing resources and SLA violations.
   - Recommend corrective actions.

7. Escalation Agent
   - Identify unacknowledged assignments.
   - Notify the next responsible authority.
   - Maintain escalation history.

8. Delivery Verification Agent
   - Request delivery confirmation.
   - Identify partial or disputed deliveries.
   - Reopen unresolved requests.

### Orchestrator Agent

Use LangGraph as the central orchestration layer.

The orchestrator must:
- Coordinate communication between agents.
- Delegate tasks based on request status.
- Maintain shared request context.
- Handle failed agent execution and retries.
- Prevent conflicting actions.
- Request human approval for life-critical decisions.
- Maintain an observable agent execution trace.

### Agent Execution Requirements

- Every agent must expose structured inputs and outputs.
- Every agent must have explicitly defined tools.
- Use deterministic services for critical calculations.
- LLM decisions must be validated before execution.
- Record agent decisions, tool calls, outcomes and failures.
- Support MockLLM execution without internet access.
- Demonstrate at least three agents collaborating
  on one emergency request during the demo.

Do not implement agents as independent chatbots.
They must collaborate through a shared workflow
and produce measurable operational outcomes.


---

## 15. Acceptance criteria (Codex must make these pass)

1. `make demo` starts API + web and seeds data; control room loads with live data in under 60 s.
2. Ingesting the 30 hand-written multilingual examples yields correct need_type for >= 90% and correct urgency for >= 80% using MockLLM alone.
3. Duplicate collapse: injected duplicates are linked to a canonical request; canonical trust_score increases.
4. Illegal state transitions return 409; every transition appears in the audit trail.
5. Matching never over-allocates stock (property test with random inputs) and respects road passability and vehicle capacity.
6. Matching 500 requests x 100 resources completes in < 3 s on a laptop.
7. A request left unaccepted beyond SLA appears as a gap within one detector cycle and triggers the correct escalation level.
8. Unacknowledged escalation moves up one level; all steps logged with timestamps.
9. Blocking a road invalidates affected dispatches and triggers a re-match.
10. DELIVERED without requester response never becomes VERIFIED automatically; it produces a `DELIVERED_UNVERIFIED` gap and a spot-check task.
11. A "partial" reply reopens the request.
12. The scenario script runs end to end deterministically and the Impact page shows both baseline and ReliefChain numbers.
13. Entire demo works with **no internet and no API keys**.
14. Frontend has no console errors in the demo flow; Playwright smoke test passes.

---

## 16. Safety, ethics, privacy (include in README and in the pitch)

- **Human in the loop:** AI proposes, humans can override any priority/dispatch; all overrides need a reason.
- **No autonomous triage of life-critical cases without review:** low-trust CRITICAL requests go to a human review queue.
- **Privacy:** store minimal PII, mask phone numbers in UI by default, retention limit config (e.g. purge after 30 days), role-based access.
- **Abuse and spam:** rate limits, phone verification, geo consistency checks, corroboration.
- **Bias check:** report fulfillment rate by ward and by vulnerability group on the Impact page to expose inequitable outcomes.
- **Failure modes:** documented fallbacks (LLM down > rule-based; OR-Tools down > greedy; no internet > cached forecast; no smartphone > SMS keywords).
- **Transparency:** every match shows its explanation; the forecast model shows feature contributions.

---

## 17. Differentiators to maximize winning odds

Build these in roughly this order after the core is stable:
1. **The "Unresolved Right Now" screen**, a single view showing stuck requests plus owner. This is the memorable image.
2. **Live failure injection during the demo** (judges can click "block road" or "drop stock" and watch the system self-heal).
3. **Unmet-need output** ("what's missing, where") that converts a coordination tool into a supply-resilience tool (ties directly to the track).
4. **Baseline vs ReliefChain** comparison with honest labeling.
5. **Multilingual intake** (Tamil/Hindi/English code-mixed), a strong India-relevance signal.
6. **Low-connectivity path**: SMS keyword mode and volunteer app offline queue.
7. **Anticipatory pre-positioning** linking forecast to the lifecycle.
8. **Audit trail / accountability** framed for governance and post-disaster review.
9. **Equity metrics** by ward and vulnerable group.
10. **Replay mode**: record a scenario and replay it for post-event learning.
11. **Open API + adapter design** so it plugs into existing dashboards (NDMA-style systems, Sahana Eden, Ushahidi) rather than replacing them.
12. **Stretch:** WhatsApp Cloud API live adapter; image analysis of citizen photos (flood depth estimate, damaged-road check) to improve urgency and road status; heatwave variant (cooling centers, ORS, vulnerable elderly check-ins) as a second hazard module showing generality.

---

## 18. Deliverables for the hackathon

- Working repo with `make demo`.
- README with architecture diagram, setup, scenario walkthrough, limitations.
- `DECISIONS.md` with assumptions and tradeoffs.
- 90-second demo script (below) and 5-minute pitch outline.
- Screenshots / GIF of the Control Room and the failure-injection moment.

### 90-second demo script
1. (10 s) "Dashboards show where the flood is. They don't show which request is still unanswered. ReliefChain does."
2. (20 s) Start scenario: surge arrives, duplicates collapse, matches appear on the map.
3. (25 s) Block a road live > reroute. Agency ignores a critical request > escalation fires > auto-reassign.
4. (15 s) Boats run out > "Ward 9 short by 2 boats", the unmet-need panel.
5. (10 s) Requester says "partial" > request reopens, nothing is falsely closed.
6. (10 s) Impact page: baseline vs ReliefChain. Close with the question: "Which request is unresolved, and whose job is it? Now you can answer that."

---

## 19. Coding standards for Codex

- Type hints everywhere; Pydantic validation at all boundaries.
- Pure functions for matching/scoring so they are unit-testable.
- No secrets in the repo; `.env.example` only.
- Deterministic seeds for all simulations.
- Small commits per milestone with a passing test run.
- Keep each service file under ~400 lines; split if larger.
- Log structured JSON; include request_id in every log line related to a request.
- Do not add features outside this spec until Section 15 passes; record ideas in `DECISIONS.md`.

---

## 20. Optional stretch module: Heatwave/Power-shortage variant

Reuse the same lifecycle engine with different need types (COOLING, ORS, POWER_BACKUP, ELDERLY_WELLNESS_CHECK) and a forecast driven by temperature and grid load. Demonstrates that the engine is hazard-agnostic: **"one lifecycle engine, many climate shocks."** Only build after all acceptance criteria pass.
