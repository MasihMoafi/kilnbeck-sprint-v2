# ADR-4: Trust as Architecture

## Status
Approved

## Context
Quentron's value is rooted entirely in the accuracy and credibility of its findings. Presenting a single incorrect savings figure to a client destroys their trust. We must establish a system where the agent is forced to abstain or flag uncertainties, and we must build an automated evaluation harness to prevent regressions as LLMs or prompts change.

## Decision: Dual-Key Verification & Semantic Confidence Gating

We implement an architecture where every finding must pass a deterministic verification gate before it can be presented as an opportunity card, and we evaluate agent quality continuously using an automated test harness.

```
       +---------------------------------------------+
       |               Raw Finding                   |
       | (what, evidence, value, tariff, confidence) |
       +----------------------+----------------------+
                              |
                              v
       +----------------------+----------------------+
       |           Deterministic Verification        |
       |  - Range present?                           |
       |  - Stated assumptions?                      |
       |  - Stated confidence level (H/M/L)?         |
       +----------------------+----------------------+
                              |
                              +---> Fail: REFUSE (ok: false, log warning)
                              |
                              +---> Pass: Proceed to Semantic Gate
                              |
                              v
       +----------------------+----------------------+
       |                Semantic Gate                |
       | - Any unresolved schedule conflicts?       |
       | - Any raw data quality flags?               |
       +----------------------+----------------------+
                              |
                              +---> Yes: Demote to "Needs Verification"
                              |          (Show finding, hide monetary £)
                              |
                              +---> No: Publish "Opportunity Card"
```

### 1. Confidence Semantics & Gating
Every finding is rated: **High**, **Medium**, or **Low** confidence. The rules for publishing are strict:
* **High Confidence:** Finding is anchored to a direct, observed natural experiment (e.g. Christmas shutdown baseload or contractor check-meter drop) with clean billing data. Published directly as an **Opportunity Card**.
* **Medium Confidence:** Finding has strong statistical indicators (e.g. clear night-time load regression) but lacks a baseline shutdown window. Published with a clear warning that field verification is required to tighten the range.
* **Low Confidence / Unresolved Conflicts:** If the site has active data quality flags (like the 10x scaling error) or schedule contradictions, the finding is gated. The agent is forced to **abstain** from presenting a value range. Instead, it generates a **"Needs Verification" task** showing what is suspected and what specific question the customer must answer to unlock the calculation.

### 2. The Evaluation Harness (Regression Protection)
To stop quality from regressing when prompts or models are updated:
* We run an automated test suite ([decisions/golden_set.md](file:///home/masih/Desktop/works/energy/kilnbeck-sprint/decisions/golden_set.md)) containing historical, edge-case datasets with known correct outputs.
* Every commit runs the agent loop offline against these datasets.
* The test runner parses the agent's final JSON responses and asserts:
  1. No hallucinated point estimates (must be ranges).
  2. Immediate HITL triggers when conflicts are loaded.
  3. Proper error handling when tools are simulated to fail.
  4. Accuracy of corrected daily totals.

### 3. Weekly Metrics & Rollback Triggers

We track three core metrics weekly on our telemetry dashboard:
1. **Tool Exception Rate (TER):** The percentage of agent conversations that encountered a Python tool error. *Target: < 0.1%*.
2. **Hallucination Detection Rate (HDR):** The percentage of outputs where the agent mentioned a number not returned by the execution engine. *Target: 0%*.
3. **HITL Acceptance Rate:** The percentage of times a user confirmed a schedule conflict surfaced by the agent. *Target: > 80%* (low numbers suggest the agent is spamming false conflicts).

### Rollback Trigger
If the **TER exceeds 0.5%** or any **HDR event > 0** is detected in production, we trigger an automatic rollback to the previous stable model version or prompt release.
