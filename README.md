# Quentron Builder Evaluation — Kilnbeck Sprint Submission

This repository contains the completed deliverables for the Kilnbeck Brewing Co. energy evaluation sprint. All code is built using only the Python standard library (no external dependencies required, no API keys needed).

---

## Executive Summary of Findings

1. **Annual Savings Opportunity:** **£30,400 to £36,500 / year**
   * *Air Compressor:* £14.2k–£18.3k/yr by shutting it off outside operational shifts (saving 13.5 kW NOH leak draw).
   * *Cold Store:* £16.2k–£18.2k/yr by resolving the control regression that occurred on April 1, 2026.
2. **One-Time Billing Refund:** **£80,958** (due to a 10x meter scaling error from April 18 to May 9, 2025).

---

## Quick Start (Run in < 1 minute)

### 1. Run the Data Diagnostics
To execute the raw data cleaning and analysis pipeline and view the calculated energy metrics, run:
```bash
python3 analysis/diagnostic.py
```

### 2. Run the Offline Agent Demo
To start the interactive chat agent loop using the mock client, run:
```bash
python3 agent/demo.py
```
To run through the checklist:
1. Type `What's wasting energy at Kilnbeck?`
2. When prompted for HITL confirmation, type: `Ah — yes, we do brew some Friday evenings. Forgot about that.`
3. Type `So how much will I save exactly?`
4. Type `What do you remember about this site?`
5. Type `exit` to quit.

---

## Submission Structure

```
kilnbeck-sprint/
├── README.md               ← This file (quick start & summary)
├── FINDINGS.md             ← Act I: Diagnostic Memo, savings decomposition, site walk list
├── ANSWERS.md              ← Act III: Kill list, pack critique, and 30-day plan
├── AI_USE.md               ← AI Use Note details
├── analysis/
│   └── diagnostic.py       ← Act I: Data cleaning & calculation script
├── agent/
│   ├── tools.py            ← Harness integration: Six tool implementations
│   └── demo.py             ← Harness integration: Offline interactive chat loop
└── decisions/
    ├── adr0_framework.md   ← ADR-0: Framework scan & recommendation
    ├── adr1_agent_system.md← ADR-1: Centralized agent loop architecture
    ├── adr2_memory.md      ← ADR-2: Event-sourced database memory architecture
    ├── adr4_trust.md       ← ADR-4: Trust as architecture & evaluation harness
    ├── economics.md        ← 100-site model computation costs (£5.04/site/month)
    ├── golden_set.md       ← Test harness: First seven golden test cases
    └── tom_message.md      ← Tom's Message (177 words)
```

---

## System Requirements
* Python 3.10 or higher
* Standard library only (no `pip install` required)
