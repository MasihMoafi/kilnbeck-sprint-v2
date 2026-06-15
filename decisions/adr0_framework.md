# ADR-0: Framework Scan & Recommendation

## Status
Proposed / Approved

## Context
Quentron needs a runtime framework for its agent system to execute the find-diagnose-recommend loop for hundreds of industrial sites. The runtime must handle deterministic data-processing pipelines, interactive human-in-the-loop (HITL) gates, and long-term state tracking. 

## Options Considered

### Option 1: LangGraph (Stateful Agentic Graphs)
* *Description:* A framework by LangChain designed to build stateful, multi-actor applications with support for cyclic graph structures, custom states, and human-in-the-loop checkpoints.
* *Pros:* Excellent built-in support for conversational state, memory persistence, and standard LLM tool-calling loops. Large ecosystem.
* *Cons:* Steep learning curve, high runtime overhead, significant library lock-in, and challenging to debug when complex state transitions occur inside generic graphs.

### Option 2: Temporal (Durable Workflow Engine)
* *Description:* A highly reliable, production-grade distributed orchestrator that guarantees workflow execution (durable state, infinite retries, and failure recovery) using code-as-configuration.
* *Pros:* Unmatched reliability for multi-day, retry-heavy processes (like awaiting utility portal syncs). Guarantees that actions (like issuing reports) are executed exactly once.
* *Cons:* Requires running a separate Temporal server cluster. It has high infrastructure complexity, introduces noticeable execution latency, and has very poor built-in primitives for interactive LLM conversation routing.

### Option 3: Custom Thin Orchestration Loop (Roll Your Own)
* *Description:* A custom python runtime (like the harness shipped in `llm_client.py`) that implements a simple state machine and tool execution loop.
* *Pros:* Extremely lightweight, zero external dependencies (no library lock-in), total debuggability, lowest possible latency (<10ms overhead), and extremely easy for a single engineer to maintain and audit.
* *Cons:* Requires building your own persistence, queueing, and retry wrappers for long-running processes.

---

## Comparison Matrix

| Evaluation Criteria | Option 1: LangGraph | Option 2: Temporal | Option 3: Custom Thin Loop |
| :--- | :--- | :--- | :--- |
| **Control & Debuggability** | Medium (obscured by graph framework) | High (fully deterministic code) | **Very High** (plain Python code) |
| **State & Retry Handling** | Medium (in-memory/DB checkpoints) | **Very High** (durable workflows) | Medium (requires manual DB writes) |
| **Cost & Latency** | Medium (~100ms framework lag) | Low (but runs infrastructure) | **Very Low** (<2ms framework lag) |
| **Lock-in & Reversibility** | High (bound to LangChain ecosystem) | Medium (bound to Temporal SDK) | **None** (plain Python) |
| **Uptime / Reliability** | Medium | **Very High** (infinite retries) | High (if run on serverless/queues) |
| **Team-of-One Maintainability**| Medium | Low (requires devops overhead) | **Very High** (standard stdlib script) |

---

## Recommendation & Decision
We choose **Option 3: Custom Thin Orchestration Loop**. 

### Rationale
At Quentron's current stage, the core analysis must remain deterministic and auditable. The model's role is not to perform complex autonomous reasoning, but rather to route conversations and trigger structured tool outputs. LangGraph introduces unnecessary complexity and dependency churn, while Temporal introduces heavy devops overhead. 

A custom orchestrator written in standard Python:
1. Meets the strict **under 2-second user response time** requirement (adding <5ms framework overhead vs. LangGraph's 100ms+).
2. Keeps infrastructure costs near zero, staying comfortably within the **£100/site/month compute budget**.
3. Allows a team-of-one to audit every line of code without guessing how graph state is serialized.

## Revisit Conditions
We will revisit this decision if:
1. The agent logic grows to require complex multi-actor negotiation that a simple routing loop cannot handle.
2. The team expands and needs a standard enterprise workflow tool like Temporal to manage long-term distributed state across different microservices.
