# Agent Harness — Full Loop, No API Required

Quentron's product is an agent a brewery MD talks to. Here you build a thin but **real** version of that agent around your Act I analysis — orchestration loop, tools, memory, confidence gating, human-in-the-loop — using a model client that runs **fully offline**.

`llm_client.py` ships a `MockLLM`: a deterministic policy that behaves like a competent tool-calling model. It decides *which* tool to call next based on conversation state; **all numbers, findings and text content flow from YOUR tool implementations**. If your tools are right, the conversation is right. This is intentional: we are evaluating your system, not a model's eloquence — and it means every candidate's demo runs identically, anywhere, free.

Wiring in a real model instead (or as well) earns credit — see `adapter_example.py` for any OpenAI-compatible endpoint, including local models via Ollama. Build so that swapping `MockLLM` for a real model is a one-line change. That abstraction is part of the test.

## What you build

1. **Tools** per `tools_spec.md` — six functions wrapping your Act I analysis plus simple memory read/write (a JSON file or SQLite is fine; your ADR-2 is the five-year answer, this is the one-week one).
2. **The loop** — feed conversation + tool results to the client, execute returned tool calls, append results, repeat until a final answer. Handle a tool raising an exception without the agent lying about it.
3. **The gate** — before any savings figure reaches the user, it passes your confidence check: findings below your threshold are presented as "needs verification", with the reason. Hard rule: **the model never invents a number** — if a figure didn't come from a tool, it doesn't reach the user.
4. **HITL** — when the analysis contradicts the site notes (it will), the agent must pause and ask the human to confirm before quantifying anything that depends on the answer.

## The demo (drives the mock; record it in your walkthrough)

```
User: What's wasting energy at Kilnbeck?
→ agent gathers context, runs analysis, HITs the schedule contradiction,
  asks for confirmation
User: Ah — yes, we do brew some Friday evenings. Forgot about that.
→ agent adjusts, presents the genuine waste finding as an opportunity
  card: what, evidence, £/yr RANGE, confidence, recommended action
User: So how much will I save exactly?
→ agent holds the line: range + assumptions + what verification would
  tighten it. It does not produce a point estimate. Ever.
User: What do you remember about this site?
→ agent reads memory: confirmed schedule exception, the finding, the date
```

## Acceptance checklist

- [ ] `python demo.py` runs the conversation above offline, end to end
- [ ] Numbers in the conversation match your FINDINGS.md
- [ ] Kill one tool deliberately → agent degrades honestly, doesn't hallucinate
- [ ] Memory persists across two runs
- [ ] (Credit) same demo runs against a real model via the adapter
