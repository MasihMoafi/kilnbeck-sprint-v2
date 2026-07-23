---
name: Kilnbeck Energy Evaluation
type: completed energy-analysis sprint submission with an offline agent prototype
---

# Kilnbeck Energy Evaluation

**The supplied site data contains enough inconsistency to make cleaning the data part of the energy analysis.**

This repository is my completed Kilnbeck Brewing Co. sprint submission: a standard-library Python diagnostic pipeline, documented energy findings, architecture decisions, and an offline mock-agent demonstration.

From the sprint dataset and stated tariff assumptions, the analysis estimates **£30.4k–£36.5k/year of addressable electricity savings** plus a potential **£80,958 billing-overcharge recovery**. These are analytical opportunities—not realized savings or a guaranteed utility refund.

## Quick start

No external Python packages or API keys are required.

```bash
git clone https://github.com/MasihMoafi/kilnbeck-sprint-v2.git
cd kilnbeck-sprint-v2
python3 analysis/diagnostic.py
```

Expected result: the diagnostic script loads the supplied electricity, production, and cold-store files, applies the documented data corrections, and prints the calculated baseload/waste metrics.

Run the offline agent demonstration separately:

```bash
python3 agent/demo.py
```

Example interaction:

```text
What's wasting energy at Kilnbeck?
Ah — yes, we do brew some Friday evenings. Forgot about that.
So how much will I save exactly?
What do you remember about this site?
exit
```

The agent demo uses a mock/offline client. It demonstrates the interaction and human-confirmation design; it is not evidence of a deployed production agent.

## The problem

The raw site files contain multiple data-quality faults alongside genuine operational changes. Treating every value as trustworthy would produce materially wrong energy and cost conclusions.

The analysis therefore first resolves known anomalies, then decomposes non-operational-hours load and tests whether observed step changes are consistent with specific waste hypotheses.

## Headline findings

Using the assumptions documented in [`FINDINGS.md`](FINDINGS.md):

| Finding | Estimated opportunity | Evidence used |
| --- | ---: | --- |
| Air-compressor non-operational-hours load | **£14.2k–£18.3k/year** | 13.5 kW difference between normal weekend non-refrigeration baseload and Christmas-shutdown minimum |
| Cold-store control regression | **£16.2k–£18.2k/year** | Check-meter drop from ~10.9 kW to ~3.5 kW, followed by an April 1, 2026 baseline increase |
| Spring 2025 meter-scaling anomaly | **£80,958 potential recovery** at 25p/kWh | 22-day period identified as 10× scaled; estimated 323,832 kWh over-report |

The annual values assume a **25p/kWh** reference tariff, with sensitivity calculations at 20p and 30p documented in [`FINDINGS.md`](FINDINGS.md).

The compressor and cold-store values are addressable-savings estimates. Physical site inspection, tariff/bill verification, and operational confirmation can change them.

## Data corrections

The diagnostic pipeline explicitly handles the issues found in the supplied files:

- 10× electricity-meter scaling from April 18 to May 9, 2025;
- 100× production-volume unit shift from September 1, 2025;
- daily-total mismatch caused by omitted end-of-day intervals;
- January 2026 negative-value/sign-flip anomalies;
- missing DST intervals;
- duplicate-date handling.

The correction logic is inspectable in [`analysis/diagnostic.py`](analysis/diagnostic.py); the reasoning and assumptions are documented in [`FINDINGS.md`](FINDINGS.md).

## How it works

```text
raw electricity + production + cold-store data
                    ↓
         explicit cleaning rules
                    ↓
      operating / non-operating split
                    ↓
       baseload decomposition
                    ↓
       waste hypotheses + costs
                    ↓
 findings / site checks / agent tools
```

The analysis uses the stated Monday–Friday, 07:00–17:00 operating schedule as an input assumption and explicitly records that schedule conflicts require human confirmation rather than silent inference.

## Current state

### Implemented and inspectable

- Standard-library data-cleaning/diagnostic pipeline.
- Calculated non-operational-hours and baseload metrics.
- Findings memo with assumptions, sensitivity ranges, confidence levels, and disconfirming evidence.
- Offline agent demo and six tool-oriented harness components.
- Architecture decision records for framework, agent system, memory, trust/evaluation, and economics.
- Seven documented golden regression cases derived from actual data issues.

### Implemented but not production-verified

- The agent loop is an offline demonstration rather than a deployed service.
- The seven golden cases in [`decisions/golden_set.md`](decisions/golden_set.md) are an approved evaluation specification; the README does not claim they are all continuously automated in CI.
- Savings estimates have not been confirmed by a physical site visit or post-intervention measurement.
- The potential billing recovery has not been verified against the actual utility invoice/CT configuration in this repository.

### Planned / recommended validation

- Physical compressor/leak inspection.
- Cold-store controller/setpoint verification.
- Weekend clamp-meter audit.
- Physical billing-meter CT-ratio check.
- Canning-line standby inspection.

These are validation actions from the findings, not shipped software features.

### Intentionally unsupported / out of scope

- Gas-consumption analysis.
- Detailed solar/battery feasibility.
- Production deployment of the agent prototype.
- Claims of realized customer savings.

## What sets this submission apart

The useful design choice is that uncertainty is carried into the deliverable rather than hidden:

- raw-data defects are documented and corrected explicitly;
- financial outputs show assumptions and sensitivity ranges;
- findings include “what would change my mind” conditions;
- schedule conflicts are designed to stop at a human-confirmation gate rather than being silently labeled as waste.

## Evals and test series

[`decisions/golden_set.md`](decisions/golden_set.md) defines seven regression cases based on failures encountered in the dataset:

1. 10× meter scaling;
2. liters-to-hectoliters unit shift;
3. truncated daily totals;
4. sign-flipped readings;
5. DST null intervals;
6. regression after an operational fix;
7. conflict-to-human-confirmation gating.

The diagnostic script itself provides the reproducible numerical path for the current dataset:

```bash
python3 analysis/diagnostic.py
```

What the current evidence supports: the documented calculations and data-cleaning logic can be inspected and rerun against the supplied sprint data.

What it does not prove: that the identified equipment is physically responsible for every inferred load, that the savings will be realized, or that a utility will issue the estimated refund.

## Repository map

```text
README.md
FINDINGS.md
ANSWERS.md
AI_USE.md
analysis/
  diagnostic.py
agent/
  tools.py
  demo.py
decisions/
  adr0_framework.md
  adr1_agent_system.md
  adr2_memory.md
  adr4_trust.md
  economics.md
  golden_set.md
  tom_message.md
```

## Future development

For this sprint submission, the next meaningful work is **validation**, not more architecture: verify the physical equipment assumptions and convert the highest-value golden cases into automated regression tests if the prototype is continued.
