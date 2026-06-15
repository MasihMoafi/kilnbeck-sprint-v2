# Quentron Economics: Cost Model for 100 Sites

## Status
Approved

## Arithmetic (Monthly Cost for 100 Sites)

We assume 100 sites of Kilnbeck's scale (18 months of half-hourly data, minute-by-minute sub-metering, and daily analysis checks).

### 1. Model Inference (LLM) Costs
* **Daily Cron Analysis Check:** 1 run per site per day. (Requires `get_site_context`, `run_noh_analysis`, `create_opportunity_card`, `write_memory` = 4 LLM turns).
* **Ad-hoc User Conversations:** We assume 2 chat sessions per site per day, averaging 3 turns each (6 turns).
* **Total Daily Turns per Site:** 10 turns.
* **Token Count per Turn:** 4,000 input tokens (context + tools specification), 500 output tokens.
* **Daily Tokens per Site:**
  * Input: 10 × 4,000 = 40,000 tokens.
  * Output: 10 × 500 = 5,000 tokens.
* **Monthly Tokens for 100 Sites:**
  * Input: 40,000 × 30 × 100 = 120,000,000 tokens (120M).
  * Output: 5,000 × 30 × 100 = 15,000,000 tokens (15M).
* **Cost (using Claude 3.5 Sonnet / GPT-4o pricing: $3.00/1M input, $15.00/1M output):**
  * Input Cost: 120M × $3.00 = $360.00
  * Output Cost: 15M × $15.00 = $225.00
  * **Total LLM Cost:** **$585.00/month** (approx. **£450/month**).

### 2. Compute Costs (Serverless & Database)
* **Serverless Executions (AWS Lambda):** 1,000 executions/day (daily cron + chat requests). Very low CPU execution time (~200ms per run).
  * Cost: 30,000 executions × $0.0000167 = $0.50/month.
* **Database (PostgreSQL on AWS RDS - db.t4g.medium):** Holds site memory, event logs, and metadata.
  * Cost: **$40.00/month** (approx. **£31/month**).

### 3. Storage Costs (S3 for raw CSV data)
* Kilnbeck's raw data size: ~3 MB. For 100 sites: 300 MB.
  * Cost: negligible (< **$0.10/month**).

### 4. Monitoring & Telemetry (Datadog or similar)
* Basic metrics and log ingestion.
  * Cost: **$30.00/month** (approx. **£23/month**).

---

### Total Estimated Cost (100 Sites): £504 / month
* **Per Site Cost:** **£5.04 / month**
* This is safely below our **£100/site/month** limit, leaving a 95% margin.

---

## Dominant Cost & Optimization

The **dominant cost** is **LLM Inference** (representing over 85% of the total budget).

### Design Decisions to Cut LLM Costs in Half
1. **Semantic Caching & Summarization:**
   Instead of passing the entire raw chat history and full site context in every turn, we materialize the site's profile into a small Markdown summary (compressing 4,000 input tokens down to 1,000 tokens). This cuts input token cost by **75%**.
2. **Hybrid Routing (LLM Classification):**
   Use a tiny, cheaper model (like Llama-3-8B or Claude 3.5 Haiku at $0.25/1M input tokens) for standard routing and conversational turns. Only invoke the expensive model (Sonnet/GPT-4o) when a complex, unstructured diagnostic task is triggered. This reduces the average cost per token by **80%**.
