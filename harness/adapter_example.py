"""Optional: drive the same agent loop with a real model.

Works with any OpenAI-compatible chat-completions endpoint — including
LOCAL models via Ollama (https://ollama.com): `ollama run qwen2.5:14b`
exposes http://localhost:11434/v1 with no account, no key, no network.

This is deliberately a sketch, not a library. Making it production-shaped
is ADR-1 territory. stdlib only (urllib) so it runs anywhere.
"""
from __future__ import annotations
import json, os, urllib.request
from llm_client import LLMClient, ModelReply, ToolCall

SYSTEM = """You are Quentron, an AI energy manager for a brewery.
Rules you never break:
- Facts and numbers come ONLY from tool results in the conversation.
- If analysis contradicts what the site owner claimed, call
  request_confirmation before quantifying anything schedule-dependent.
- Savings are ranges with assumptions and a confidence level, never a
  single figure.
- If a tool fails, say so plainly and suggest the next step.
Respond EITHER with a tool call EXACTLY as JSON:
  {"tool": "<name>", "arguments": {...}}
OR with final text for the user (no JSON)."""


class RealLLM(LLMClient):
    def __init__(self,
                 base_url: str = os.getenv("LLM_BASE_URL",
                                           "http://localhost:11434/v1"),
                 model: str = os.getenv("LLM_MODEL", "qwen2.5:14b"),
                 api_key: str = os.getenv("LLM_API_KEY", "ollama")):
        self.base_url, self.model, self.api_key = base_url, model, api_key

    def complete(self, messages: list[dict], tools: list[str]) -> ModelReply:
        chat = [{"role": "system",
                 "content": SYSTEM + "\nAvailable tools: " + ", ".join(tools)}]
        for m in messages:
            role = "user" if m["role"] == "tool" else m["role"]
            prefix = f"[tool:{m['name']} result] " if m["role"] == "tool" else ""
            chat.append({"role": role, "content": prefix + m["content"]})
        req = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps({"model": self.model, "messages": chat,
                             "temperature": 0}).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            content = json.load(r)["choices"][0]["message"]["content"].strip()
        try:  # tool call?
            obj = json.loads(content)
            if isinstance(obj, dict) and "tool" in obj:
                return ModelReply(tool_call=ToolCall(obj["tool"],
                                                     obj.get("arguments", {})))
        except json.JSONDecodeError:
            pass
        return ModelReply(text=content)
