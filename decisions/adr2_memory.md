# ADR-2: Memory Architecture

## Status
Approved

## Context
A site's context—operating schedules, equipment inventory, past findings, verified savings, and user corrections—must persist for years. The system must handle contradictions over time (e.g. founder says "closed weekends" in Jan, data shows activity in June, a new operations manager claims "Saturdays are cleaning days" in October) and remain fully inspectable by non-technical staff.

## Decision: Event-Sourced Semantic Memory with Relational Context

We choose an **append-only, event-sourced schema** stored in a relational database (PostgreSQL), combined with a flat, human-readable JSON/Markdown export for inspection. 

```
               +--------------------------------------+
               |          Incoming Event              |
               | (e.g. HITL schedule correction)      |
               +------------------+-------------------+
                                  |
                                  v
               +------------------+-------------------+
               |       Append-Only Event Log          |
               | - ID, Timestamp, Source, EventType   |
               | - Payload (JSON)                     |
               +------------------+-------------------+
                                  |
                                  v
               +------------------+-------------------+
               |      Materialized State Engine       |
               |  (Reconciles chronological facts)    |
               +------------------+-------------------+
                                  |
                                  +---> Current Schedule Fact
                                  +---> Confirmed Savings Fact
                                  +---> Historical Conflict Logs
```

### 1. Data Representation & Write Policy
* **Append-Only Write Policy:** We *never* run `UPDATE` queries on historical facts. If a user corrects a schedule, we write a new `CorrectionEvent` to the log that references the older event it overrides. 
* **State Materialization:** To know the current schedule or equipment list, a state builder runs a chronological scan over the event log for that site. This preserves the full audit trail: who changed what, when, and based on what data.

### 2. Handling Contradictions
* When a new fact is loaded (e.g., "Saturdays are closed") that conflicts with data patterns (e.g., Saturday draws 700 kWh) or prior events, the system creates a `ConflictEvent` flag.
* The orchestrator blocks the agent from making schedule-dependent savings claims until a human resolves the conflict.
* If a new ops manager updates the schedule 6 months later, the system records it as a new event, resolving the conflict chronologically. The system remembers *both* states: "Prior to Oct 2026, the site was closed on Saturdays (wasting energy); after Oct 2026, Saturday cleaning was approved (making the load legitimate)."

### 3. Database vs. Plain Text: Honest Trade-offs

* **When is a Database the WRONG answer?**
  A relational database is the wrong answer for presenting the context to a non-technical founder or audit client. Founders cannot query SQL tables. If they want to inspect the site's record, they need a plain, version-controlled Markdown summary page. 
* **When is Plain Text the WRONG answer?**
  Plain text (like a raw `.md` or `.txt` file) is the wrong answer for runtime agent retrieval and structural query processing. An LLM trying to read a single giant text file of 5 years of chaotic chat history will waste context tokens, suffer from retrieval distraction, and fail to parse chronological overrides reliably.

### 4. Reconciliation: Hybrid Storage
We use a hybrid approach:
* **Runtime:** The agent queries a structured relational schema (`events` table) to build its context payload.
* **Founder Inspection:** The system automatically renders a clean, human-readable Markdown profile page (e.g. `kilnbeck_profile.md`) from the database events on every update. This page displays the active facts, past overrides, and verified outcomes in simple bullet points.
