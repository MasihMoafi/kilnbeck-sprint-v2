# ADR-1: The Agentic System Architecture

## Status
Approved

## Context
We need to design the system architecture that automates the full loop (detect → diagnose → recommend → implement → verify → archive) for hundreds of industrial sites. The system must meet strict SLA constraints:
1. **Deterministic analysis:** The model must never calculate or invent a number; all figures must come from code.
2. **Compute budget:** Under £100/site/month at scale.
3. **Response time:** Under 2 seconds for user queries.
4. **Reliability:** 99.9% uptime from day one.

## Decision: Structured Tool-Calling Loop with Deterministic Core

We implement a **centralized orchestrator** pattern. The LLM acts as the routing brain, while the actual energy calculations, data cleaning, and database persistence live in structured, deterministic code tools.

```
       +--------------------+
       |   User Interface   |
       +---------+----------+
                 | (Query)
                 v
     +-----------+-----------+
     |  Custom Orchestrator  | <--------+
     +-----------+-----------+          |
                 | (Context + tools)    |
                 v                      |
      +----------+----------+           |
      | LLM Router (Llama3) |           |
      +----------+----------+           |
                 | (Tool Call)          |
                 v                      |
      +----------+----------+           |
      |   Deterministic     | ----------+
      |  Execution Engine   | (Tool Result)
      +---------------------+
```

### 1. Separation of Concerns (LLM vs Code)
* **LLM (Reasoning):** Responsible *only* for mapping user intent to specific tools (e.g. `run_noh_analysis`), prompting for missing inputs, formatting natural language responses, and routing the conversation.
* **Execution Engine (Deterministic Code):** Responsible for loading CSVs, cleaning sensor data (handling sign-flips, 10x meter errors), and performing all mathematical calculations (integrating power, computing cost savings, and running baseload regressions). No LLM has access to raw data calculation.

### 2. State & Conversation Management
* The orchestrator maintains the conversation state as an append-only JSON structure in a PostgreSQL database (re-loaded on every turn).
* The context size is kept short by summarizing historical runs and using structured database queries rather than raw data logs in the prompt.

### 3. Human-in-the-Loop (HITL) Gate
* When a data conflict is detected (e.g. `get_site_context` or `run_noh_analysis` returns `"conflicts"`), the orchestrator blocks the LLM from outputting any savings cards. 
* The system halts execution, changes the state to `AWAITING_INPUT`, and prompts the user to resolve the contradiction. Once confirmed, the answer is saved to memory, and the analysis is rerun.

### 4. Meeting Constraints

* **Under 2-Second Latency:** 
  To meet this, we use a fast, local/hosted LLM (e.g., Llama-3-8B-Instruct or Claude-3-Haiku) via structured tool calling. Since the analysis code runs locally in python (<100ms) and the LLM inference takes ~1.5s, the total round-trip remains under 1.8 seconds.
* **Under £100/month/site Budget:**
  At scale, 100 sites running daily checks will consume:
  * 1 daily analysis check + 10 user queries/day = 11 LLM turns/day per site.
  * 11 calls × 30 days = 330 queries/month.
  * 330 queries × 4,000 tokens/query = 1.32M tokens/month.
  * At Claude-3-Haiku pricing ($0.25/1M input, $1.25/1M output), the model cost is **under £2.00/site/month**, leaving 98% of the budget for raw compute/storage.
* **99.9% Uptime from Day One:**
  The system is built on **stateless serverless functions (AWS Lambda or Google Cloud Functions)** triggered by events (cron for daily data fetches, HTTP for user queries). Standard database transactions are used for memory updates, preventing race conditions.

### 5. Failure Modes & Mitigations
* **Tool Exception:** If a Python data-parsing tool crashes (e.g., corrupted CSV), the orchestrator catches the error, prevents the LLM from hallucinating a response, and outputs: *"The analysis pipeline reported an error [ErrorName]. We are investigating the data export format."*
* **LLM JSON Output Failure:** If the LLM generates invalid JSON for a tool call, the orchestrator catches the parsing exception and sends the error back to the LLM as a system message to force a retry (up to 3 times).

## Revisit Conditions
* Revisit if serverless compute starts exceeding budget due to massive CSV file transfers (in which case we would implement edge-caching of pre-processed summaries).
