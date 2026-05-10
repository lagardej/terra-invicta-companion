# Architecture — General Design Note

## Context

Local-only application. Autowatches Terra Invicta savefiles, imports and processes their data, and exposes datatables, graphs, and data evolution around entities (factions, nations, etc.).

Latency is a non-concern. Simplicity and rusticity are guiding principles.

---

## Functional Core / Imperative Shell (FCIS)

The architecture enforces a hard boundary between pure logic and side-effecting code.

**Functional Core** — no I/O, no bus calls, no database writes:

- Domain logic (data transformation, validation, event construction)
- All functions here are pure: same input → same output, no observable side effects

**Imperative Shell** — all side effects live here:

- Inbound transport adapters (filesystem watcher, HTTP handlers, bus subscribers)
- Outbound transport adapters (bus publishers, WS broadcaster)

This boundary is the primary guard against complexity drift. If a function in the core needs to "do something", that's a design error — lift the effect into the shell instead.

---

## Module / use case structure

The codebase is organized into **bounded contexts** (modules), each subdivided into **use cases**.

```
src/tic/
  <module>/
    __init__.py
    shared/             # shared between use cases within the module
      _events.py        # domain events, private to the module
      ...
    <use_case>/
      __init__.py
      core/             # functional core: pure logic, no side effects
      shell/            # imperative shell(s), one file per transport/direction
        <transport>_<direction>.py
```

Nothing goes directly in a module or use case directory — all logic lives inside `core/`, `shell/`, or `shared/`.

For simple use cases with a single file per layer, the directory structure can be flattened using a prefix:

```
<use_case>/
  __init__.py
  core_<name>.py
  shared_<name>.py
  shell_<transport>_<direction>.py
```

The same flattening applies at the module level for shared files:

```
<module>/
  __init__.py
  shared_events.py    # replaces shared/_events.py
  <use_case>/
    ...
```

Each use case is self-contained: its core, its shell(s), and its types. The shell is the only entry point from the outside world.

Shared infrastructure (bus, event store, document store, base types) lives in `src/tic/shared/` and `src/tic/_infra/`. Cross-cutting config and wiring lives in `src/tic/_config/`.

---

## Shell naming

Shell modules follow a `shell_{transport}_{direction}` naming scheme. The transport and direction must be readable from the filename alone — no need to open the file.

**Direction:** `in` (inbound) or `out` (outbound).

**Transport examples:** `filesystem`, `http`, `ws`, `cli`, `bus`, `pubsub`, `reqrep`.

When a use case has only a few shell endpoints, a flat module is acceptable:

```
shell_bus_in.py
shell_http_in.py
shell_ws_out.py
```

When a use case has many shell endpoints, group them in a `shell/` directory — the `{transport}_{direction}` pattern is preserved in the filenames:

```
shell/
  bus_in.py
  bus_out.py
  filewatch_in.py
  http_in.py
  ws_out.py
```

The class inside the module mirrors the filename in PascalCase: `BusIn`, `HttpIn`, `BusOut`, `WsOut`, etc.

---

## Event types, communication and boundaries

All domain processing communicates via the bus. The read side bypasses it entirely — Shells query the read model directly.

The flow within a use case: the inbound shell receives external input, calls the core (pure), then publishes the resulting events onto the bus. Other shells react as subscribers — read model projections, outbound integration publishers, WS broadcasters. No shell calls another shell directly.

The domain uses event sourcing without aggregates. Each processing run is independent: no concurrent writes, no conflict resolution. Events are the source of truth; the read model is a projection that can be rebuilt from the event log at any time.

Events are classified into three categories by their scope and boundary-crossing behaviour:

### DomainEvent — within bounded context

- Represents a state change within a single bounded context
- Persisted to the event store (historical record)
- Never imported by another context — use integration events instead

Domain events live in `src/tic/<context>/shared/_events.py` (or `shared_events.py` in the flat variant) — private to the module.

### IntegrationEvent — across bounded contexts

- Crosses context boundaries
- Published on the shared bus for inter-context communication
- Never persisted (transient signal, not historical record)

Defined in `src/tic/shared/events/` — publicly importable by any context. The importing context depends on this shared contract, not on the exporting context's internal structure.

### Event — use-case-scoped coordination (not persisted)

- Internal to a use case; not persisted to the event store
- Used for dispatching within a shell module when handling multiple event types
- Never crosses context boundaries

Treat like a DomainEvent — keep in `_events.py` and don't export outside the context.

### Read-model projections

A projection within a context listens to **domain events** from its own context, not integration events — the projection is an internal concern.

If an external context needs to react, it subscribes to an integration event published by the outbound shell.

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

```
Browser (HTMX) → GET /resource → HttpIn → Read model → Jinja2 fragment
```

### Write (HTTP + WebSocket feedback) — CQRS

Handler validates the command synchronously (400 on bad input). If valid, publishes to the bus and returns `202 Accepted`. Domain processing is async. Outcome is pushed back to the browser via WebSocket.

```
Browser → POST /resource → HttpIn → [bus] → Core
                         ↓
                    202 Accepted

Core → Succeeded / Failed → [bus] → WS broadcaster → toast
```

---

## Error handling

Errors are first-class domain events, handled identically to success events: written to the read model and forwarded to the browser via WebSocket.

No special error plumbing. The event log is the source of truth for processing status.

Command validation failures are rejected synchronously by the HTTP handler before the bus is involved — standard 4xx response.
