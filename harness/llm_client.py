"""Quentron sprint harness — provider-agnostic model client + offline mock.

You build the agent loop and tools around `LLMClient`. The shipped `MockLLM`
is a deterministic tool-routing policy: it decides WHAT to do next; every
fact and number comes from YOUR tools. Swap in a real model via
`adapter_example.py` — your loop should not need to change.

stdlib only. Python 3.10+.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class ModelReply:
    """Either a tool call to execute, or final text for the user."""
    tool_call: ToolCall | None = None
    text: str | None = None


@dataclass
class LLMClient:
    """Interface. complete() receives the running transcript:
    messages = [{"role": "user"|"assistant"|"tool", "content": str,
                 "name": str (tool messages only)} ...]
    and the available tool names. Returns a ModelReply.
    """
    def complete(self, messages: list[dict], tools: list[str]) -> ModelReply:
        raise NotImplementedError


def _tool_results(messages: list[dict]) -> dict[str, dict]:
    """Most recent result per tool, parsed."""
    out: dict[str, dict] = {}
    for m in messages:
        if m.get("role") == "tool":
            try:
                out[m["name"]] = json.loads(m["content"])
            except Exception:
                out[m["name"]] = {"ok": False, "raw": m["content"]}
    return out


class MockLLM(LLMClient):
    """Deterministic policy imitating a competent tool-calling model.

    Routing logic (read it — it documents the expected agent behaviour):
      1. No site context yet           -> get_site_context
      2. Unconfirmed schedule conflict -> request_confirmation (once)
      3. No analysis yet               -> run_noh_analysis
      4. Analysis ok, no card yet      -> create_opportunity_card for the
                                          top finding marked is_waste=true
      5. Card exists, not remembered   -> write_memory
      6. Otherwise                     -> final text composed ONLY from
                                          tool outputs (never invented)
    Asking "how much exactly" produces the hold-the-line answer.
    Asking "what do you remember" routes to read_memory.
    """

    SITE = "kilnbeck"

    def complete(self, messages: list[dict], tools: list[str]) -> ModelReply:
        res = _tool_results(messages)
        last_user = next((m["content"].lower() for m in reversed(messages)
                          if m["role"] == "user"), "")

        if "remember" in last_user and "read_memory" in tools:
            if "read_memory" not in res:
                return ModelReply(tool_call=ToolCall("read_memory",
                                  {"site_id": self.SITE, "kind": None}))
            mem = res["read_memory"]
            return ModelReply(text="Here is what I have on record:\n"
                              + json.dumps(mem, indent=2, default=str))

        if "exactly" in last_user or "how much" in last_user:
            card = res.get("create_opportunity_card")
            if card and card.get("ok"):
                c = card.get("card", card)
                return ModelReply(text=(
                    "I won't give you a single figure — here is what I can "
                    "stand behind:\n"
                    f"  Range: {c.get('value_range_gbp_yr', 'see card')}\n"
                    f"  Assumptions: {c.get('assumptions', 'see card')}\n"
                    f"  Confidence: {c.get('confidence', '?')}\n"
                    "A short verification window (sub-metering the suspect "
                    "circuit or a controlled switch-off test) would tighten "
                    "this to a number you can take to the bank."))
            return ModelReply(text="I need to complete the analysis before "
                                   "discussing figures.")

        if "get_site_context" not in res:
            return ModelReply(tool_call=ToolCall("get_site_context",
                                                 {"site_id": self.SITE}))

        ctx = res["get_site_context"]
        conflicts = ctx.get("conflicts") or []
        confirmed = "request_confirmation" in res
        analysed = "run_noh_analysis" in res

        # Confirm BEFORE quantifying if context already shows a conflict;
        # also confirm after analysis surfaces one.
        if conflicts and not confirmed:
            q = ("The data shows activity outside the operating hours you "
                 f"described ({conflicts[0]}). Can you confirm what runs "
                 "then, so I don't count legitimate work as waste?")
            return ModelReply(tool_call=ToolCall("request_confirmation",
                              {"question": q, "context": str(conflicts[0])}))

        if not analysed:
            return ModelReply(tool_call=ToolCall("run_noh_analysis",
                              {"site_id": self.SITE, "period": None}))

        analysis = res["run_noh_analysis"]
        if not analysis.get("ok"):
            return ModelReply(text=(
                "The analysis tool reported a problem rather than a result: "
                f"{analysis.get('error', 'unknown error')}. I'd rather tell "
                "you that than guess. Next step: "
                f"{analysis.get('suggestion', 'investigate the data issue')}."))

        a_conflicts = analysis.get("conflicts") or []
        if a_conflicts and not confirmed:
            q = ("Before I quantify anything: the meter shows "
                 f"{a_conflicts[0]} — what is that?")
            return ModelReply(tool_call=ToolCall("request_confirmation",
                              {"question": q, "context": str(a_conflicts[0])}))

        if "create_opportunity_card" not in res:
            findings = [f for f in analysis.get("findings", [])
                        if f.get("is_waste")]
            if not findings:
                return ModelReply(text="No defensible waste finding emerged. "
                                       "Here is what I checked: "
                                       + json.dumps(analysis.get("checked",
                                                                 []), indent=2))
            top = max(findings,
                      key=lambda f: f.get("value_gbp_yr_low", 0))
            return ModelReply(tool_call=ToolCall("create_opportunity_card",
                              {"site_id": self.SITE, "finding": top}))

        card = res["create_opportunity_card"]
        if not card.get("ok"):
            return ModelReply(text=("I found something but can't yet present "
                                    "it responsibly: "
                                    f"{card.get('reason', '?')}"))

        if "write_memory" not in res:
            return ModelReply(tool_call=ToolCall("write_memory",
                              {"site_id": self.SITE, "kind": "finding",
                               "content": card.get("card", card)}))

        c = card.get("card", card)
        return ModelReply(text=(
            "Here's where we landed.\n"
            f"  Finding: {c.get('what', '?')}\n"
            f"  Evidence: {c.get('evidence', '?')}\n"
            f"  Worth: {c.get('value_range_gbp_yr', '?')} per year "
            f"(assumptions: {c.get('assumptions', '?')})\n"
            f"  Confidence: {c.get('confidence', '?')}\n"
            f"  Next step: {c.get('action', '?')}\n"
            "I've saved this to the site record."))


@dataclass
class AgentLoop:
    """Reference skeleton — replace/extend freely. Shows the contract."""
    client: LLMClient
    tools: dict[str, Callable[..., dict]]
    messages: list[dict] = field(default_factory=list)
    max_steps: int = 12

    def ask(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        for _ in range(self.max_steps):
            reply = self.client.complete(self.messages,
                                         list(self.tools.keys()))
            if reply.text is not None:
                self.messages.append({"role": "assistant",
                                      "content": reply.text})
                return reply.text
            call = reply.tool_call
            try:
                result = self.tools[call.name](**call.arguments)
            except Exception as e:  # honest degradation, not hallucination
                result = {"ok": False, "error": f"{type(e).__name__}: {e}",
                          "suggestion": "check tool implementation/inputs"}
            self.messages.append({"role": "tool", "name": call.name,
                                  "content": json.dumps(result,
                                                        default=str)})
        return "Step limit reached — see transcript."
