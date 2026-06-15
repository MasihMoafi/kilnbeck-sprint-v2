# Quentron Golden Test Set: First Seven Cases

## Status
Approved

## Context
These seven golden test cases protect Quentron's analysis quality as our LLM prompts, model versions, and code pipelines change. They draw directly on real bugs and edge cases discovered in the Kilnbeck dataset.

---

### Case 1: The 10x Scaling Correction
* **Scenario:** Electricity data includes a 3-week period where all values are multiplied by 10 (e.g. Apr 18 – May 9, 2025).
* **Why it earns a slot:** Billing meter scaling errors are common during physical CT transformer modifications on-site.
* **What regression it catches:** Prevents the system from publishing a 10x overstated savings card (which would destroy customer trust) or failing to detect the scaling change in the baseline.

### Case 2: The Liters-to-Hectoliters Unit Shift
* **Scenario:** Production volume log suddenly increases by 100x starting from a specific date (e.g. Sept 1, 2025) because the brewery's software switched from hl to liters.
* **Why it earns a slot:** Software migrations are the primary source of corrupted historical records.
* **What regression it catches:** Catches failures in the unit-normalization layer, preventing a 100x error in Specific Energy Consumption (SEC) calculations.

### Case 3: The Truncated Daily Sum (September Bug)
* **Scenario:** The reported daily total column is missing the last hour of data (columns `23:30` and `24:00`), causing a systematic daily under-report of ~30 kWh.
* **Why it earns a slot:** Utility exports are notoriously buggy and often truncate DST days or day-end hours in their daily total aggregations.
* **What regression it catches:** Verifies that our calculation engine always derives daily consumption directly by summing the 48 half-hourly rows, rather than trusting the reported `Daily Total` column.

### Case 4: The Sign-Flip day
* **Scenario:** Raw half-hourly electricity data contains negative float values (e.g., `-75.2` kWh) during a normal weekday shift.
* **Why it earns a slot:** Sensor exports frequently suffer from sign-inversion bugs during power flow direction switches.
* **What regression it catches:** Prevents mathematical calculation crashes or under-reporting of true daily energy consumption. The test asserts that the engine takes the absolute values of these cells.

### Case 5: The DST Missing Columns (Nulls)
* **Scenario:** The start of Daylight Saving Time (e.g., March 30, 2025) results in empty cells for the non-existent hours of `01:30` and `02:00`.
* **Why it earns a slot:** DST transitions happen twice a year and routinely crash naive date-time parsers.
* **What regression it catches:** Catches NullPointerExceptions or parse errors in our data-loading scripts. Asserts that the parser treats these slots as 0.0 or interpolates them safely.

### Case 6: The April 1st Regression Detection
* **Scenario:** Main meter baseline consumption drops from 28.8 kW to 21.5 kW for 6 weeks, then jumps back up to 29.8 kW starting exactly on a new date.
* **Why it earns a slot:** Operational fixes often fail over time (staff bypass controls, settings are reset, or contractor exports end). 
* **What regression it catches:** Verifies that the agent automatically flags when a previously resolved finding has regressed, alerting the user to re-investigate the issue.

### Case 7: The Conflict-to-HITL Gate
* **Scenario:** The site profile notes claim the site is closed on weekends, but the raw data shows an average baseline load of 30 kW on Saturdays. The database contains no record of user confirmation.
* **Why it earns a slot:** The model must never make schedule-dependent claims without verifying if the weekend load is legitimate (e.g. approved cleaning) or waste.
* **What regression it catches:** Asserts that the agent loop stops and triggers `request_confirmation` before publishing any opportunity cards, verifying that the human-in-the-loop gate cannot be bypassed.
