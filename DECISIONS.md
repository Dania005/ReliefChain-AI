# Implementation decisions

- **Offline persistence:** The runnable app uses SQLite through Python's standard library so it can start without a database service. SQLModel table definitions are included for the intended Postgres-compatible schema; persistence remains behind a small adapter.
- **LangGraph is the orchestrator:** Eight typed specialist nodes collaborate through a shared request context. Agent traces persist each tool and outcome. Deterministic MockLLM extraction is the default; no key or network is needed.
- **Matching:** OR-Tools is attempted when available, with a deterministic nearest-first greedy fallback. Route feasibility is intentionally simplified to a local road-block flag in this demo.
- **Forecast and impact:** The demo shows transparent synthetic risk features and clearly labeled illustrative baseline figures; those figures are not presented as measured outcomes.
- **Scope:** This blank workspace is implemented as a coherent control-room demo first. The full 500-request data generator, robust SMS/WhatsApp adapters, complete volunteer and agency pages, and operational identity/privacy controls remain follow-up work.
- **Frontend fonts:** Use system fallbacks so the UI does not need a font CDN at runtime.
