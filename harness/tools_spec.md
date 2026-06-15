# Tool Contracts

Six tools. Names and signatures are fixed (the mock client routes on them); internals are yours. Every tool returns a JSON-serialisable dict and **must include** `"ok": true/false` and, where a finding is produced, `"confidence": "high"|"medium"|"low"` plus `"evidence": <short string>`.

```
get_site_context(site_id: str) -> dict
    Site profile: operating schedule (claimed + any confirmed corrections
    from memory), equipment notes, known meters. Sources: site_notes.md
    + memory. Must surface unresolved contradictions in a
    "conflicts" field.

run_noh_analysis(site_id: str, period: str|None) -> dict
    Your Act I pipeline as a callable. Returns NOH ratio, baseload kW,
    decomposition, candidate waste findings, data-quality flags.
    Must run from raw CSVs (no cached conclusions).

request_confirmation(question: str, context: str) -> dict
    Human-in-the-loop. In demo.py this prompts on stdin. Returns the
    human's answer. The agent must not quantify schedule-dependent
    findings before this returns on a conflicted site.

create_opportunity_card(site_id: str, finding: dict) -> dict
    Formats a finding into: what / evidence / £yr range + assumptions /
    confidence / recommended next action. REFUSES (ok:false, reason)
    if finding lacks a range, assumptions, or confidence.

write_memory(site_id: str, kind: str, content: dict) -> dict
    Persist: confirmed facts, corrections, findings, outcomes.
    Timestamped. Append-only (corrections reference what they correct
    — do not silently overwrite history).

read_memory(site_id: str, kind: str|None) -> dict
    Retrieve, most-recent-first, contradictions surfaced not resolved.
```

**Design note:** `create_opportunity_card`'s refusal behaviour is the product's character in one function. The agent that ships a card without a defensible range is the agent that loses the customer — make the refusal path as polished as the success path.
