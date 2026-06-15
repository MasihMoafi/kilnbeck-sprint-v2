# AI Use Note

## Tools/models used
* **Antigravity** (AI coding assistant, powered by Gemini 3.5 Flash)

## The single best prompt of my week (verbatim) and why it worked
> *"Write a python script to calculate the weekend daily consumption of the main meter over the entire 18-month period. This will show exactly when this high weekend consumption began, which is crucial for estimating the annual waste value."*

*Why it worked:* By directing the model to analyze the weekend consumption chronologically over the entire 18-month period rather than focusing only on the Feb-Mar cold store logs, it revealed the hidden step change on April 1, 2026. This proved that the cold store fix regressed, showing that the customer went back to wasting energy, which is the key business justification for Quentron's continuous monitoring model.

## The worst model failure I caught
Initially, the model noticed that the cold store current dropped by exactly a factor of 3 on Feb 15, 2026 (from ~15.4 A to ~5.1 A) and hypothesized it was a CT wiring/configuration error by the refrigeration contractor. I pushed back and directed it to verify if the main meter also dropped by the same amount (~177 kWh/day) on weekends. By writing a comparison script, we proved the main meter did drop, confirming the energy savings were physically real and not just a check-meter calculation error.

## What I overrode or rewrote by hand, and why
I overrode the model's suggestion to include critiques of the startup's hiring funnel (the abstract games, online forms) in Act III, Q2. I refocused the critique strictly on the technical contradictions in their evaluation pack (the premature 99.9% uptime SLA and the rigid 2-second latency constraint). I wanted to ensure the response was highly professional, constructive, and technically focused.

## Anything submitted that I could NOT rebuild alone
None. I guided the creation of the codebase, verified the logic of every data cleaning step, and can fully rebuild, explain, and defend every number and architectural decision in this submission.
