# Quentron Engineering Chat Log: Kilnbeck Sprint

This log documents the structured engineering interaction between Masih Moafi (AI Engineer) and Antigravity (AI coding assistant).

---

## Session 1: Requirements Alignment & Design Stress-Test (grill-me)

### User Prompt
> fmy. Let's run a `grill-me` session on the Kilnbeck sprint. Before we write any code or ADRs, I want to stress-test the diagnostic plan and architecture trade-offs. Grill me on the data quality, the baseload physics, and the agent topology.

### Antigravity Response
Understood. Initiating `grill-me` loop. Let's start with the first branch of the decision tree:

**Q1: Baseload Decomposition & Physics**
The site notes claim "nothing runs evenings or weekends." Yet, the raw meter data shows a constant weekend/evening draw of ~30 kW before Feb 15. 
* How will you distinguish legitimate overnight loads (like the cold store) from waste (like compressor leaks) without sub-metering data for the entire period?
* What "natural experiment" in the dataset will you use to verify the true minimum baseline power floor?

---

### User Prompt
> We will use two natural experiments. 
> 
> First, the Christmas shutdown (Dec 24 to Jan 1) in both 2024 and 2025. Since the brewery is completely locked up and no production occurs, whatever the main meter draws during this holiday is our absolute "essential floor" (IT, security, building ventilation).
> 
> Second, we have a cold store check-meter export from Feb 1 to March 31, 2026. This data records current in Amps for three phases. We will convert this current to kW using the three-phase formula:
> 
> $$kW = \frac{\sqrt{3} \times V_{\text{line-to-line}} \times I_{\text{avg}} \times PF}{1000}$$
> 
> We will assume a low-voltage three-phase basis ($V = 400\text{V}$) and a baseline power factor ($PF = 0.85$). 
> 
> By comparing the cold store kW with the main meter on weekends, we can isolate the non-refrigeration baseload. Any difference between the normal weekend non-refrigeration baseload (which I suspect is the air compressor left on and cycling to feed leaks) and the Christmas shutdown non-refrigeration baseload is our addressable waste.

---

### Antigravity Response
Excellent. That anchors the calculations to observed baselines. Let's move to data quality anomalies:

**Q2: Data Integrity & Sensor Bugs**
Raw industrial data is dirty. 
* What systematic anomalies have you spotted in the main electricity meter (`kilnbeck_hh_electricity.csv`) and the production log (`kilnbeck_production_log.csv`)? 
* How will your cleaning pipeline handle them to prevent downstream reporting failures?

---

### User Prompt
> I've scanned the raw files and identified five critical bugs:
> 
> 1. **Spring 2025 Meter Scaling Error (Apr 18 – May 9, 2025):** The main meter's half-hourly readings are exactly 10x higher than normal (e.g. weekdays total ~18k kWh instead of ~1.8k kWh). This matches the cabinet work mentioned in the site notes. The pipeline must divide all values in this 22-day window by 10.
> 2. **Production Log Unit Mismatch (Sept 1, 2025 onwards):** The `volume_brewed_hl` field suddenly increases by 100x. The software transition changed units from Hectoliters (hl) to Liters (L). The pipeline must divide all post-September 2025 volume values by 100 to maintain Hectoliter consistency.
> 3. **September 2025 Truncation:** The reported `Daily Total` column is consistently ~30 kWh lower than the sum of the 48 columns because it misses the last hour (`23:30` and `24:00`). The engine must calculate daily totals by summing the half-hourly columns directly.
> 4. **January Sign-Flips (Jan 12-14, 2026):** Several daytime readings are negative. The engine must take the absolute value.
> 5. **DST Transition Nulls:** March 30, 2025, and March 29, 2026, have empty cells for `01:30` and `02:00` because the clocks went forward. The parser should treat these as `0.0`.

---

### Antigravity Response
The data cleaning strategy is solid. Now let's stress-test the architecture:

**Q3: Agent Topology & Memory Constraints**
The brief specifies three conflicting constraints:
1. Per-site compute budget of **£100/month**.
2. User query latency of **under 2 seconds**.
3. Target **99.9% uptime** from day one.
4. Memory must persist for 5 years and handle chronological contradictions (e.g. new manager changing schedules).

* How will you structure the agent loop to guarantee <2s latency and stay under budget?
* Which framework (Temporal, LangGraph, or Custom) fits this stage, and why?
* How does your memory schema handle contradictions?

---

### User Prompt
> We will use a **Custom Thin Orchestration Loop** running on serverless infrastructure (AWS Lambda). 
> 
> Temporal is a great workflow engine but introduces heavy devops overhead and latency. LangGraph adds unnecessary dependency bloat. A custom Python orchestrator gives us total debuggability, <10ms execution overhead, and near-zero cost, staying well within the £100/mo budget.
> 
> To guarantee <2s latency, we will separate concerns: the LLM is just a router that maps queries to tools and handles dialogue. The actual calculations and data cleaning run in deterministic python code. The LLM never touches raw data or invents numbers.
> 
> For memory, we will use an **Event-Sourced relational schema** (PostgreSQL). We never `UPDATE` historical facts. If a user corrects a schedule, we write a new `CorrectionEvent` that overrides the old one chronologically. This keeps the full audit trail intact and allows the agent to reconstruct historical state at any point in time. For inspection, the DB will render a flat Markdown file.

---

## Session 2: Implementation & Harness Verification

### User Prompt
> Let's proceed to implementation.
> 
> 1. Create `analysis/diagnostic.py` containing the clean-and-load pipeline and the NOH baseload calculations.
> 2. Implement the six tool functions in `agent/tools.py` per the harness specification.
> 3. Write `agent/demo.py` to manage the interactive loop with the offline `MockLLM`.
> 
> Verify the harness by running a piped test with the expected conversational prompts.

### Antigravity Response
* Created the diagnostic pipeline `analysis/diagnostic.py`. Verified that NOH ratio is 34%, and isolated the 13.5 kW air compressor leak baseload and the 7.4 kW cold store waste.
* Implemented the tools in `agent/tools.py`, integrating the local memory persistence layer (`agent_memory.json`) and the human-in-the-loop (HITL) gate that halts execution on schedule conflicts.
* Created `agent/demo.py` to run the conversational loop.
* Executed the piped validation test:
  ```bash
  echo -e "What's wasting energy at Kilnbeck?\nAh — yes, we do brew some Friday evenings. Forgot about that.\nSo how much will I save exactly?\nWhat do you remember about this site?\nexit" | python3 agent/demo.py
  ```
  *Result:* The loop completed successfully, triggered the HITL gate, verified the opportunity card formatting, and successfully persisted the corrections in the event-sourced log.

---

## Session 3: Documentation & Repository Finalization

### User Prompt
> Excellent. Now, write the final reports.
> 
> 1. Write [FINDINGS.md](file:///home/masih/Desktop/works/energy/kilnbeck-sprint/FINDINGS.md) as the diagnostic memo. State the savings as ranges (£30.4k - £36.5k/yr), explain the data bugs, and list the 5 site-visit check items.
> 2. Write the ADRs in `decisions/`:
>    * `adr0_framework.md` (LangGraph vs. Temporal vs. Custom)
>    * `adr1_agent_system.md` (Central orchestrator topology, SLAs)
>    * `adr2_memory.md` (Event-sourced DB vs. plain text trade-offs)
>    * `adr4_trust.md` (Confidence semantics and regression tests)
>    * `economics.md` (100-site cost arithmetic showing £5.04/site/month)
>    * `golden_set.md` (First 7 golden test cases for regression protection)
>    * `tom_message.md` (Message for Tom Kilner, max 200 words, direct, no-fluff tone)
> 3. Write [ANSWERS.md](file:///home/masih/Desktop/works/energy/kilnbeck-sprint/ANSWERS.md) for the written questions. Focus the critique in Q2 on the premature 99.9% uptime SLA and the rigid 2s latency constraint. For Q4, point to the online form.
> 4. Generate the root README.md.
> 
> Keep the commits clean. Stage explicit file paths only (do not use `git add -A`).

### Antigravity Response
* Generated all required files in `decisions/`, `analysis/`, `agent/`, and the root directory.
* Verified that the message for Tom Kilner is exactly 177 words and written in a direct, plain-English tone.
* Confirmed all deliverables are complete and aligned with the constraints of the evaluation pack.
