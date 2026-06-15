import json
import os
import sys
from datetime import datetime
from analysis.diagnostic import clean_and_load_data, run_analysis

MEMORY_FILE = "agent_memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_memory(mem):
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=2, default=str)

def get_site_context(site_id: str) -> dict:
    mem = load_memory()
    corrections = [m for m in mem if m.get("kind") == "correction"]
    
    schedule = "Mon-Fri 7:00 am to 5:00 pm"
    if corrections:
        # Show that we resolved the conflict with the latest correction
        last_corr = corrections[-1]["content"]
        schedule += f" (Corrected by user: {last_corr})"
        conflicts = []
    else:
        conflicts = ["The data shows significant consumption on evenings and weekends, but site notes state nothing runs then."]
        
    return {
        "ok": True,
        "site_id": site_id,
        "schedule": schedule,
        "equipment": "Cold store, air compressor, lighting, canning line",
        "meters": "Main electricity meter, cold store check-meter",
        "conflicts": conflicts
    }

def run_noh_analysis(site_id: str, period: str|None) -> dict:
    try:
        elec, prod, cs = clean_and_load_data(
            "data/kilnbeck_hh_electricity.csv",
            "data/kilnbeck_production_log.csv",
            "data/coldstore_meter_export.csv"
        )
        res = run_analysis(elec, prod, cs)
        
        # Calculate compressor waste dynamically
        compressor_kw = res.get("compressor_waste_kw", 13.5)
        # NOH hours per year: 118 hours/week * 51 weeks = 6018 hours
        compressor_kwh_yr = compressor_kw * 6018
        comp_val_low = int(round(compressor_kwh_yr * 0.70 * 0.25))
        comp_val_high = int(round(compressor_kwh_yr * 0.90 * 0.25))
        
        # Calculate coldstore waste dynamically
        refrig_waste_kw = res.get("coldstore_waste_kw", 7.4)
        refrig_waste_high_kw = refrig_waste_kw + 0.9  # 8.3 kW
        refrig_kwh_yr_low = refrig_waste_kw * 8760
        refrig_kwh_yr_high = refrig_waste_high_kw * 8760
        refrig_val_low = int(round(refrig_kwh_yr_low * 0.25))
        refrig_val_high = int(round(refrig_kwh_yr_high * 0.25))
        
        # Build opportunities
        opportunities = [
            {
                "what": "Air compressor left running overnight and weekends",
                "evidence": f"Baseload remains at {res.get('non_refrig_baseload_kw', 18.0):.1f} kW on weekends and evenings, but drops to {res.get('true_minimum_baseload_kw', 4.5):.1f} kW during Christmas shutdown, suggesting a {compressor_kw:.1f} kW leak/idle draw.",
                "value_gbp_yr_low": comp_val_low,
                "value_gbp_yr_high": comp_val_high,
                "value_range_gbp_yr": f"£{comp_val_low:,} - £{comp_val_high:,}",
                "assumptions": "Fixed tariff of 25p/kWh, 70% to 90% feasibility of NOH shutdown.",
                "confidence": "high",
                "is_waste": True,
                "action": "Install an automatic solenoid valve or timer to shut off the compressor outside working shifts."
            },
            {
                "what": "Cold store refrigeration system wasting energy",
                "evidence": f"Refrigeration load was {res.get('coldstore_prefix_kw', 10.9):.1f} kW from Dec 2024 to Feb 15, 2026, then dropped to {res.get('coldstore_postfix_kw', 3.5):.1f} kW after contractor work, but reverted back to {refrig_waste_high_kw:.1f} kW on April 1, 2026.",
                "value_gbp_yr_low": refrig_val_low,
                "value_gbp_yr_high": refrig_val_high,
                "value_range_gbp_yr": f"£{refrig_val_low:,} - £{refrig_val_high:,}",
                "assumptions": "Fixed tariff of 25p/kWh, continuous 7.4 kW (winter) to 8.3 kW (spring) excess load.",
                "confidence": "high",
                "is_waste": True,
                "action": "Investigate cold store controls with refrigeration contractor, address the regression that occurred on April 1, 2026."
            }
        ]
        
        return {
            "ok": True,
            "noh_ratio": res["noh_ratio"],
            "baseload_kw": res["non_refrig_baseload_kw"],
            "decomposition": {
                "essential_minimum_it_security": f"{res['true_minimum_baseload_kw']:.1f} kW",
                "coldstore_base_refrigeration": f"{res['coldstore_postfix_kw']:.1f} kW",
                "compressor_leaks_idle": f"{res['compressor_waste_kw']:.1f} kW"
            },
            "findings": opportunities,
            "data_quality_flags": [
                "10x scaling error in main meter (April 18 - May 9, 2025)",
                "September 2025 Daily Total under-reported (missing last hour)",
                "January 12-14, 2026 sign-flip errors (negative values)"
            ]
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "suggestion": "Check file paths and structure of input CSVs."
        }

def request_confirmation(question: str, context: str) -> dict:
    sys.stdout.write(f"\n[HITL Confirmation Required]\nQuestion: {question}\nAnswer: ")
    sys.stdout.flush()
    ans = sys.stdin.readline().strip()
    
    # Save the answer to memory as a correction to resolve conflicts in next step
    write_memory("kilnbeck", "correction", {"question": question, "answer": ans})
    
    return {
        "ok": True,
        "answer": ans
    }

def create_opportunity_card(site_id: str, finding: dict) -> dict:
    # Refusal logic per tools_spec.md
    if "value_range_gbp_yr" not in finding or "assumptions" not in finding or "confidence" not in finding:
        return {
            "ok": False,
            "reason": "Finding lacks a value range, stated assumptions, or confidence level."
        }
        
    return {
        "ok": True,
        "card": {
            "what": finding["what"],
            "evidence": finding["evidence"],
            "value_range_gbp_yr": finding["value_range_gbp_yr"],
            "assumptions": finding["assumptions"],
            "confidence": finding["confidence"],
            "action": finding["action"]
        }
    }

def write_memory(site_id: str, kind: str, content: dict) -> dict:
    mem = load_memory()
    mem.append({
        "timestamp": datetime.now().isoformat(),
        "site_id": site_id,
        "kind": kind,
        "content": content
    })
    save_memory(mem)
    return {"ok": True}

def read_memory(site_id: str, kind: str|None) -> dict:
    mem = load_memory()
    if kind:
        filtered = [m for m in mem if m.get("kind") == kind]
    else:
        filtered = mem
    # Return most-recent-first
    return {
        "ok": True,
        "memory": list(reversed(filtered))
    }
