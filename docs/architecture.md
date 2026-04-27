# Architecture — General Design Note

## Context

Local-only application. Autowatches Terra Invicta savefiles, imports and processes their data, and exposes datatables, graphs, and data evolution around entities (factions, nations, etc.).

Latency is a non-concern. Simplicity and rusticity are guiding principles.

---

## Functional Core / Imperative Shell (FCIS)

The architecture enforces a hard boundary between pure logic and side-effecting code.

**Functional Core** — no I/O, no bus calls, no database writes:

- Savefile parser
- Domain logic (data transformation, validation, event construction)
- All functions here are pure: same input → same output, no observable side effects

**Imperative Shell** — all side effects live here:

- File watcher (reads from disk)
- Bus subscribers that write the read model
- WS broadcaster
- HTTP handlers

This boundary is the primary guard against complexity drift. If a function in the core needs to "do something", that's a design error — lift the effect into the shell instead.

---

## Layers

The architecture is a hybrid CQRS + message bus. All domain processing communicates via the bus. The read side is intentionally dumb and bypasses it entirely.

```md
File watcher → [bus] → Domain / Parser → [bus] → Read model
                                                 → WS broadcaster → Browser
```

### File watcher

Monitors the savefile directory. Emits `SavefileDetected` on the bus when a new or modified save is found. Shell layer — pure I/O.

### Domain / Parser

Subscribes to `SavefileDetected`. Parses and processes the savefile. This is the **functional core**: it receives bytes, returns events. No side effects. Emits either:

- `ImportSucceeded` — data written to the read model as a side effect (in the shell)
- `ImportFailed(reason)` — error recorded in the read model (import log row)

### Read model

Updated exclusively as a side effect of domain events. Never written to directly by the HTTP layer. Mostly static from the browser's perspective — HTMX fetches fragments on demand.

### WS broadcaster

A thin bus subscriber. Forwards domain events to connected browser clients. Carries signals only — no data payload. The browser decides whether to refetch via HTMX.

---

## Aggregateless event sourcing

The domain uses event sourcing without aggregates. Classical aggregates enforce invariants before emitting events — this domain currently has none worth enforcing. Each savefile import is independent: there is no "reject if faction already exists" logic, no concurrent writes, no conflict resolution.

The pipeline is therefore: **savefile bytes → pure parse → events → read model projection**.

Events are the source of truth for import history. The read model is a projection — it can be rebuilt from the event log at any time.

**Boundary condition:** if the domain grows to include user-owned state (annotations, manual overrides, merge logic between saves), invariant enforcement will be needed. At that point, introduce aggregates surgically. The FCIS boundary makes this safe — aggregates live in the core, their persistence side effects in the shell.

---

## Web stack

- **FastAPI** — HTTP + native WebSocket support
- **Jinja2** — server-side rendering, returns HTML fragments
- **HTMX** — browser requests fragments, swaps them in. No build step, no framework.
- **Chart.js** or **Plotly.js** — graphs, reinitialized on HTMX swap
- Vanilla JS (~30 lines) — WebSocket client + toast notifications

---

## Request patterns

### Read (HTTP) — static, no bus

HTMX requests a fragment. The read handler queries the read model directly. Jinja2 renders and returns the fragment. The bus is not involved.

```md
Browser (HTMX) → GET /factions/table → Read handler → Read model → Jinja2 fragment
```

### Write (HTTP + WebSocket feedback) — CQRS

Handler validates the command synchronously (400 on bad input). If valid, publishes to the bus and returns `202 Accepted`. Domain processing is async. Outcome is pushed back to the browser via WebSocket.

```md
Browser → POST /import → Write handler → [bus] → Domain
                       ↓
                  202 Accepted

Domain → ImportSucceeded / ImportFailed → [bus] → WS broadcaster → toast
```

---

## Error handling

Errors are first-class domain events. `ImportFailed` is handled identically to `ImportSucceeded`:

- written to the read model (import log row with status and reason)
- forwarded by the WS broadcaster as a toast notification to the browser

No special error plumbing. The import log is the source of truth for processing status.

Command validation failures are rejected synchronously by the HTTP handler before the bus is involved — standard 4xx response.
