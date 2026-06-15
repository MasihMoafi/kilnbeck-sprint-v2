# Act III — Answers

## Q1 — The kill list (Three Technical Failure Modes)

1. **Ingestion Pipeline Fragility (Rank 1):**
   * *Why:* Industrial energy data is dirty, non-standard, and prone to silent failures (e.g. contractor check-meter portals changing JSON structures, meter cabinet wiring resets, or unit changes from Liters to hl). If the parser breaks, the agent either crashes or processes corrupt data, generating false opportunity cards.
   * *30-Day Mitigation:* Build a strict validation schema layer (using Pydantic/JSON Schema) that processes all incoming CSVs before they reach the agent. It will automatically flag step changes (>50% baseline jumps), negative values, and missing timestamps. We prove it works by writing unit tests using the Golden Set of corrupted logs.

2. **LLM Financial Hallucination / Over-Confidence (Rank 2):**
   * *Why:* LLMs tend to average numbers and present single point estimates confidently. If an agent presents a point-estimate savings card of £35,000 and the client only achieves £22,000, Quentron loses its most critical asset: the Finance Director's trust.
   * *30-Day Mitigation:* Enforce a strict "Dual-Key" system architecture where the LLM is physically incapable of printing a number. The value ranges and assumptions are pre-calculated by a deterministic Python engine and passed to the LLM. The agent is forced to present ranges and confidence bands.

3. **Inference Cost / Latency Ballooning at Scale (Rank 3):**
   * *Why:* As context grows with years of site history, memory events, and tools specifications, input tokens will balloon. At 100+ sites, this will cause the compute budget to exceed the £100/site/month limit and blow past the 2-second user response time SLA.
   * *30-Day Mitigation:* Implement semantic summarization for memory. Instead of dumping raw chat logs, the orchestrator compiles history into a compact Markdown summary page, reducing input tokens by 75%.

---

## Q2 — Red pen (Critique of the Evaluation Pack)

1. **Unrealistic Uptime SLAs for a Pilot:**
   * *Critique:* The brief requires "99.9% uptime from the first pilot onwards." This is a classic premature optimization. Achieving three-nines uptime requires significant devops overhead (multi-region clusters, failover DBs, robust alert channels). At the pilot stage, Quentron should optimize for speed of code shipping and feature development, not server devops.
2. **Strict 2-Second Latency Constraint:**
   * *Critique:* The constraint that the system must answer *any* user query in under 2 seconds is too rigid. While chat responses should be fast, heavy diagnostic runs (like running regression models over 18 months of half-hourly data) take time. Forcing a 2-second limit means we cannot use deep-reasoning LLMs. The constraint should separate chat turns (<2s) from diagnostic jobs (run asynchronously with a background notification).
3. **Ambiguity on Electricity Tariff:**
   * *Critique:* Stating that Tom "couldn't find the bill" and asking candidates to "decide how to handle it" leaves the core calculation metric floating. Since every savings estimate is directly multiplied by the tariff, the pack should have defined a standard UK SME reference tariff (e.g., 25p/kWh) to ensure all candidates' numbers are normalized.

---

## Q3 — Thirty days (What to prove & what exists)

* **What I choose to prove:** That we can ingest a new, unformatted, and dirty supplier CSV export and generate a validated, error-free NOH savings report within 2 minutes of upload, without any manual data preprocessing.
* **The Artifact that will exist:** A **Production-Ready Data Ingestion & Sanitization Microservice** in Python that cleans the 5 most common industrial data bugs (sign-flips, scaling offsets, missing daylight-saving rows, daily-total gaps, and unit shifts) and outputs a normalized database structure, tested against our first 3 automated golden suites.

---

## Q4 — The hardest thing

Please refer to my answer submitted in the online application form.
