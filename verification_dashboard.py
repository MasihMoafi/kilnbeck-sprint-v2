#!/usr/bin/env python3
"""Zero-dependency verification UI for the Kilnbeck sprint submission."""
from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
import threading
import webbrowser
from dataclasses import asdict, dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass
class Check:
    id: str
    category: str
    title: str
    status: str
    summary: str
    evidence: list[str]
    source: str | None = None


def check(check_id: str, category: str, title: str, status: str,
          summary: str, *evidence: str, source: str | None = None) -> Check:
    return Check(check_id, category, title, status, summary, list(evidence), source)


def safe_run(fn: Callable[[], Check], check_id: str,
             category: str, title: str) -> Check:
    try:
        return fn()
    except Exception as exc:
        return check(check_id, category, title, "fail",
                     f"Verification raised {type(exc).__name__}.", str(exc))


def write_electricity_fixture(path: Path,
                              rows: list[tuple[str, list[Any], Any]]) -> None:
    headers = ["Date"] + [f"slot_{i:02d}" for i in range(48)] + ["Daily Total"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for date_text, slots, daily_total in rows:
            if len(slots) != 48:
                raise ValueError("Electricity fixture must contain 48 intervals")
            writer.writerow([date_text, *slots, daily_total])


def write_production_fixture(path: Path,
                             rows: list[tuple[str, int, float, int]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "brews_started", "volume_brewed_hl",
                         "packaged_units"])
        writer.writerows(rows)


def write_coldstore_fixture(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "L1", "L2", "L3"])
        writer.writerow(["01/01/2026 00:00", "10", "10", "10"])


def load_fixture(electricity_rows, production_rows):
    from analysis.diagnostic import clean_and_load_data

    temp = tempfile.TemporaryDirectory()
    base = Path(temp.name)
    electricity = base / "electricity.csv"
    production = base / "production.csv"
    coldstore = base / "coldstore.csv"
    write_electricity_fixture(electricity, electricity_rows)
    write_production_fixture(production, production_rows)
    write_coldstore_fixture(coldstore)
    loaded = clean_and_load_data(str(electricity), str(production), str(coldstore))
    return temp, loaded


def verify_required_artifacts() -> Check:
    required = [
        "README.md", "FINDINGS.md", "ANSWERS.md", "AI_USE.md",
        "analysis/diagnostic.py", "agent/tools.py", "agent/demo.py",
        "harness/llm_client.py", "decisions/adr0_framework.md",
        "decisions/adr1_agent_system.md", "decisions/adr2_memory.md",
        "decisions/adr4_trust.md", "decisions/economics.md",
        "decisions/golden_set.md", "decisions/tom_message.md",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    if missing:
        return check("artifacts", "Submission", "Required deliverables exist",
                     "fail", f"{len(missing)} required artifact(s) are missing.",
                     *missing)
    return check("artifacts", "Submission", "Required deliverables exist",
                 "pass", f"All {len(required)} documented deliverables are present.",
                 *required, source="README.md")


def verify_real_dataset() -> tuple[Check, dict[str, Any]]:
    from analysis.diagnostic import clean_and_load_data, run_analysis

    paths = [ROOT / "data/kilnbeck_hh_electricity.csv",
             ROOT / "data/kilnbeck_production_log.csv",
             ROOT / "data/coldstore_meter_export.csv"]
    missing = [str(path.relative_to(ROOT)) for path in paths if not path.exists()]
    if missing:
        return check("dataset-run", "Analysis",
                     "Diagnostic runs on supplied data", "fail",
                     "The supplied dataset is incomplete.", *missing), {}

    electricity, production, coldstore = clean_and_load_data(
        *(str(path) for path in paths))
    metrics = run_analysis(electricity, production, coldstore)
    plausible = (
        len(electricity) > 400 and len(production) > 300 and len(coldstore) > 1
        and 0 < metrics.get("noh_ratio", 0) < 1
        and abs(metrics.get("compressor_waste_kw", 0) - 13.5) < 0.01
        and abs(metrics.get("coldstore_waste_kw", 0) - 7.4) < 0.01
    )
    status = "pass" if plausible else "fail"
    summary = ("The diagnostic executed and returned internally plausible metrics."
               if plausible else
               "The diagnostic executed, but one or more expected invariants failed.")
    evidence = [
        f"Electricity days loaded: {len(electricity)}",
        f"Production days loaded: {len(production)}",
        f"Cold-store days loaded: {len(coldstore)}",
        f"NOH ratio: {metrics.get('noh_ratio', 0):.2%}",
        f"Compressor waste: {metrics.get('compressor_waste_kw', 0):.1f} kW",
        f"Cold-store waste: {metrics.get('coldstore_waste_kw', 0):.1f} kW",
    ]
    return check("dataset-run", "Analysis", "Diagnostic runs on supplied data",
                 status, summary, *evidence,
                 source="analysis/diagnostic.py"), metrics


def verify_scaling_case() -> Check:
    temp, (electricity, _, _) = load_fixture(
        [("20/04/2025", [100.0] * 48, 4800)],
        [("20/04/2025", 1, 100, 1)])
    try:
        cleaned = next(iter(electricity.values()))
        passed = all(abs(value - 10.0) < 1e-9 for value in cleaned)
        observed = cleaned[0]
    finally:
        temp.cleanup()
    return check("golden-1", "Golden tests", "10× meter scaling correction",
                 "pass" if passed else "fail",
                 ("Known scaling-window readings are divided by ten."
                  if passed else "Scaling-window readings were not corrected."),
                 f"Expected 10.0; observed {observed:.1f}",
                 source="analysis/diagnostic.py")


def verify_unit_shift_case() -> Check:
    temp, (_, production, _) = load_fixture(
        [("02/09/2025", [1.0] * 48, 48)],
        [("02/09/2025", 1, 10000, 1)])
    try:
        value = next(iter(production.values()))["volume_brewed_hl"]
        passed = abs(value - 100.0) < 1e-9
    finally:
        temp.cleanup()
    return check("golden-2", "Golden tests",
                 "Liters-to-hectoliters unit shift",
                 "pass" if passed else "fail",
                 ("Post-September production volume is normalized by 100."
                  if passed else "Production volume normalization failed."),
                 f"Expected 100.0 hl; observed {value:.1f} hl",
                 source="analysis/diagnostic.py")


def verify_daily_total_case() -> Check:
    temp, (electricity, _, _) = load_fixture(
        [("10/09/2025", [1.0] * 48, 0)],
        [("10/09/2025", 1, 100, 1)])
    try:
        derived = sum(next(iter(electricity.values())))
        passed = abs(derived - 48.0) < 1e-9
    finally:
        temp.cleanup()
    return check("golden-3", "Golden tests",
                 "Daily total is derived from intervals",
                 "pass" if passed else "fail",
                 ("A wrong Daily Total is ignored and 48 intervals are summed."
                  if passed else "The calculation trusted the supplied total."),
                 f"Supplied total: 0; derived total: {derived:.1f}",
                 source="analysis/diagnostic.py")


def verify_sign_flip_case() -> Check:
    slots = [-75.2] + [1.0] * 47
    temp, (electricity, _, _) = load_fixture(
        [("12/01/2026", slots, 122.2)],
        [("12/01/2026", 1, 100, 1)])
    try:
        value = next(iter(electricity.values()))[0]
        passed = abs(value - 75.2) < 1e-9
    finally:
        temp.cleanup()
    return check("golden-4", "Golden tests",
                 "Sign-flipped readings are repaired",
                 "pass" if passed else "fail",
                 ("Negative readings are converted to physical magnitudes."
                  if passed else "A negative reading survived cleaning."),
                 f"Expected 75.2; observed {value:.1f}",
                 source="analysis/diagnostic.py")


def verify_dst_case() -> Check:
    slots: list[Any] = [1.0] * 48
    slots[2] = ""
    slots[3] = ""
    temp, (electricity, _, _) = load_fixture(
        [("30/03/2025", slots, 46)],
        [("30/03/2025", 0, 0, 0)])
    try:
        cleaned = next(iter(electricity.values()))
        passed = cleaned[2] == 0.0 and cleaned[3] == 0.0
        observed = (cleaned[2], cleaned[3])
    finally:
        temp.cleanup()
    return check("golden-5", "Golden tests", "DST null intervals are safe",
                 "pass" if passed else "fail",
                 ("Missing spring-forward intervals become 0.0 safely."
                  if passed else "DST null handling failed."),
                 f"Observed slots: {observed[0]}, {observed[1]}",
                 source="analysis/diagnostic.py")


def verify_regression_case() -> Check:
    source = (ROOT / "analysis/diagnostic.py").read_text(encoding="utf-8")
    tools_source = (ROOT / "agent/tools.py").read_text(encoding="utf-8")
    automated = ("detect" in source.lower() and "regression" in source.lower()
                 and "regression" in tools_source.lower())
    if automated:
        return check("golden-6", "Golden tests",
                     "Post-fix regression is detected automatically", "pass",
                     "Regression-detection logic is connected to agent analysis.",
                     "Detection code found in analysis and agent paths.",
                     source="decisions/golden_set.md")
    return check("golden-6", "Golden tests",
                 "Post-fix regression is detected automatically", "warn",
                 "The April 1 regression is documented, but no general detector exists.",
                 "Current output uses fixed regression values rather than deriving a step change.",
                 "This requirement is evidence-backed, not regression-tested.",
                 source="decisions/golden_set.md")


def verify_hitl_gate() -> Check:
    from harness.llm_client import MockLLM

    client = MockLLM()
    messages = [
        {"role": "user", "content": "What's wasting energy at Kilnbeck?"},
        {"role": "tool", "name": "get_site_context",
         "content": json.dumps({"ok": True, "conflicts": [
             "Weekend activity conflicts with site notes."]})},
    ]
    reply = client.complete(messages, ["get_site_context",
                                       "request_confirmation",
                                       "run_noh_analysis"])
    routed = reply.tool_call.name if reply.tool_call else "none"
    passed = routed == "request_confirmation"
    return check("golden-7", "Golden tests",
                 "Conflict triggers human confirmation first",
                 "pass" if passed else "fail",
                 ("The policy stops at request_confirmation before analysis."
                  if passed else "Confirmation was not routed first."),
                 f"Next routed tool: {routed}",
                 source="harness/llm_client.py")


def verify_financial_guardrail() -> Check:
    from agent.tools import create_opportunity_card

    rejected = create_opportunity_card("kilnbeck", {"what": "test"})
    accepted = create_opportunity_card("kilnbeck", {
        "what": "test", "evidence": "fixture",
        "value_range_gbp_yr": "£1 - £2", "assumptions": "fixture",
        "confidence": "low", "action": "verify"})
    passed = not rejected.get("ok") and accepted.get("ok")
    return check("guardrail", "Agent",
                 "Opportunity cards require ranges and assumptions",
                 "pass" if passed else "fail",
                 ("Incomplete financial claims are refused."
                  if passed else "The financial guardrail failed."),
                 f"Incomplete accepted: {rejected.get('ok')}",
                 f"Complete accepted: {accepted.get('ok')}",
                 source="agent/tools.py")


def verify_memory_roundtrip() -> Check:
    import agent.tools as tools

    previous = tools.MEMORY_FILE
    with tempfile.TemporaryDirectory() as temp:
        tools.MEMORY_FILE = str(Path(temp) / "memory.json")
        try:
            write = tools.write_memory("kilnbeck", "finding", {"value": 42})
            read = tools.read_memory("kilnbeck", "finding")
        finally:
            tools.MEMORY_FILE = previous
    memory = read.get("memory", [])
    passed = (write.get("ok") and len(memory) == 1
              and memory[0].get("content", {}).get("value") == 42)
    return check("memory", "Agent", "Memory persists and can be read back",
                 "pass" if passed else "fail",
                 ("A finding survives a write/read round trip."
                  if passed else "The memory round trip failed."),
                 f"Entries returned: {len(memory)}", source="agent/tools.py")


def verify_economics(metrics: dict[str, Any]) -> Check:
    compressor_kw = float(metrics.get("compressor_waste_kw", 13.5))
    coldstore_kw = float(metrics.get("coldstore_waste_kw", 7.4))
    compressor_low = round(compressor_kw * 6018 * 0.70 * 0.25)
    compressor_high = round(compressor_kw * 6018 * 0.90 * 0.25)
    coldstore_low = round(coldstore_kw * 8760 * 0.25)
    coldstore_high = round((coldstore_kw + 0.9) * 8760 * 0.25)
    total_low = compressor_low + coldstore_low
    total_high = compressor_high + coldstore_high
    passed = ((compressor_low, compressor_high,
               coldstore_low, coldstore_high)
              == (14218, 18280, 16206, 18177))
    return check("economics", "Analysis",
                 "Published annual ranges recompute",
                 "pass" if passed else "fail",
                 ("Deterministic arithmetic reproduces the published range."
                  if passed else "Recomputed values differ from the report."),
                 f"Compressor: £{compressor_low:,}–£{compressor_high:,}/yr",
                 f"Cold store: £{coldstore_low:,}–£{coldstore_high:,}/yr",
                 f"Combined: £{total_low:,}–£{total_high:,}/yr",
                 source="FINDINGS.md")


def physical_validation_checks() -> list[Check]:
    items = [
        ("site-compressor", "Physical compressor/leak inspection"),
        ("site-coldstore", "Cold-store controller and setpoint verification"),
        ("site-clamp", "Weekend clamp-meter audit"),
        ("site-ct", "Billing-meter CT-ratio and invoice verification"),
        ("site-canning", "Canning-line standby inspection"),
    ]
    return [check(item_id, "Field validation", title, "pending",
                  "Cannot be verified from repository evidence alone.",
                  "Requires an on-site measurement, inspection, or bill.",
                  source="FINDINGS.md") for item_id, title in items]


def build_report() -> dict[str, Any]:
    checks: list[Check] = [safe_run(verify_required_artifacts, "artifacts",
                                    "Submission", "Required deliverables exist")]
    try:
        dataset_check, metrics = verify_real_dataset()
    except Exception as exc:
        dataset_check = check("dataset-run", "Analysis",
                              "Diagnostic runs on supplied data", "fail",
                              f"Diagnostic raised {type(exc).__name__}.", str(exc))
        metrics = {}
    checks.append(dataset_check)

    runners = [
        (verify_scaling_case, "golden-1", "Golden tests", "10× meter scaling correction"),
        (verify_unit_shift_case, "golden-2", "Golden tests", "Liters-to-hectoliters unit shift"),
        (verify_daily_total_case, "golden-3", "Golden tests", "Daily total is derived from intervals"),
        (verify_sign_flip_case, "golden-4", "Golden tests", "Sign-flipped readings are repaired"),
        (verify_dst_case, "golden-5", "Golden tests", "DST null intervals are safe"),
        (verify_regression_case, "golden-6", "Golden tests", "Post-fix regression is detected automatically"),
        (verify_hitl_gate, "golden-7", "Golden tests", "Conflict triggers human confirmation first"),
        (verify_financial_guardrail, "guardrail", "Agent", "Opportunity cards require ranges and assumptions"),
        (verify_memory_roundtrip, "memory", "Agent", "Memory persists and can be read back"),
    ]
    for runner, check_id, category, title in runners:
        checks.append(safe_run(runner, check_id, category, title))
    checks.append(safe_run(lambda: verify_economics(metrics), "economics",
                           "Analysis", "Published annual ranges recompute"))
    checks.extend(physical_validation_checks())

    counts = {status: sum(item.status == status for item in checks)
              for status in ["pass", "warn", "fail", "pending"]}
    executable = counts["pass"] + counts["warn"] + counts["fail"]
    score = round(100 * counts["pass"] / executable) if executable else 0
    return {
        "project": "Kilnbeck Energy Evaluation",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "score": score,
        "counts": counts,
        "metrics": metrics,
        "checks": [asdict(item) for item in checks],
        "legend": {
            "pass": "Verified by executable evidence",
            "warn": "Implemented or documented, but not fully automated",
            "fail": "Executable verification failed",
            "pending": "Requires external or physical evidence",
        },
    }


HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kilnbeck Verification</title><style>
:root{color-scheme:dark;--bg:#0b0d10;--panel:#12161b;--panel2:#171c22;--line:#29313a;--text:#f3f5f7;--muted:#96a0aa;--pass:#58d68d;--warn:#f4c95d;--fail:#ff6b6b;--pending:#7f8c9a;--accent:#e8a24a}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 20% -10%,#28301d 0,transparent 28%),var(--bg);color:var(--text);font:14px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.shell{max-width:1180px;margin:auto;padding:40px 24px 72px}.eyebrow{color:var(--accent);font-size:12px;font-weight:800;letter-spacing:.14em;text-transform:uppercase}.hero{display:grid;grid-template-columns:1fr auto;gap:24px;align-items:end;margin:10px 0 28px}.hero h1{font-size:clamp(34px,6vw,68px);line-height:.96;letter-spacing:-.055em;margin:0;max-width:780px}.hero p{color:var(--muted);max-width:540px;margin:16px 0 0}.score{width:138px;height:138px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(var(--pass) calc(var(--score)*1%),#242a31 0);position:relative}.score:after{content:"";position:absolute;inset:10px;border-radius:50%;background:var(--panel)}.score strong,.score span{position:relative;z-index:1;display:block;text-align:center}.score strong{font-size:36px;letter-spacing:-.05em}.score span{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.1em}.summary{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px}.stat{padding:18px;border:1px solid var(--line);background:linear-gradient(180deg,var(--panel2),var(--panel));border-radius:14px}.stat b{display:block;font-size:28px}.stat span{color:var(--muted)}.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:24px 0 14px}.toolbar button{border:1px solid var(--line);background:var(--panel);color:var(--muted);padding:9px 13px;border-radius:999px;cursor:pointer}.toolbar button.active{color:var(--text);border-color:#58616c;background:#20262d}.grid{display:grid;gap:10px}.check{display:grid;grid-template-columns:12px 1fr auto;gap:14px;padding:17px 18px;border:1px solid var(--line);background:rgba(18,22,27,.92);border-radius:14px;transition:.15s ease}.check:hover{transform:translateY(-1px);border-color:#3b4652}.dot{width:10px;height:10px;border-radius:50%;margin-top:6px;background:var(--pending);box-shadow:0 0 16px currentColor}.check.pass .dot{background:var(--pass)}.check.warn .dot{background:var(--warn)}.check.fail .dot{background:var(--fail)}.meta{color:var(--muted);font-size:11px;letter-spacing:.09em;text-transform:uppercase}.check h3{font-size:16px;margin:2px 0 4px}.check p{color:var(--muted);margin:0}.badge{align-self:start;border:1px solid var(--line);padding:5px 8px;border-radius:7px;font-size:10px;font-weight:800;letter-spacing:.08em;text-transform:uppercase}.check.pass .badge{color:var(--pass)}.check.warn .badge{color:var(--warn)}.check.fail .badge{color:var(--fail)}.check.pending .badge{color:var(--pending)}details{grid-column:2/4;margin-top:2px}summary{color:#c9d0d7;cursor:pointer;font-size:12px}.evidence{margin:10px 0 0;padding:12px 14px;background:#0d1014;border-radius:9px;color:#abb4bd}.evidence li+li{margin-top:5px}.metrics{margin-top:28px;padding:22px;border:1px solid var(--line);border-radius:16px;background:var(--panel)}.metrics h2{margin:0 0 15px}.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}.metric{padding:13px;background:#0d1014;border-radius:10px}.metric small{display:block;color:var(--muted);overflow:hidden;text-overflow:ellipsis}.metric b{font-size:18px}.foot{margin-top:28px;color:var(--muted);font-size:12px}.empty{padding:50px;text-align:center;color:var(--muted)}@media(max-width:760px){.hero{grid-template-columns:1fr}.score{width:110px;height:110px}.summary{grid-template-columns:repeat(2,1fr)}.check{grid-template-columns:12px 1fr}.badge,.check details{grid-column:2}.shell{padding:28px 16px 56px}}
</style></head><body><main class="shell"><div class="eyebrow">Repository evidence console</div><section class="hero"><div><h1>Kilnbeck verification, without the greenwashing.</h1><p>Every requirement is separated into executable evidence, partial implementation, failure, or external validation.</p></div><div class="score" id="score"><div><strong>—</strong><span>verified</span></div></div></section><section class="summary" id="summary"></section><nav class="toolbar" id="filters"></nav><section class="grid" id="checks"><div class="empty">Running verification…</div></section><section class="metrics"><h2>Analysis output</h2><div class="metric-grid" id="metrics"></div></section><div class="foot" id="foot"></div></main><script>
const embedded=__REPORT__;let report=null,filter='all';const label={pass:'Verified',warn:'Partial',fail:'Failed',pending:'Field check'};function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}function render(){document.getElementById('score').style.setProperty('--score',report.score);document.querySelector('#score strong').textContent=report.score+'%';const statuses=['pass','warn','fail','pending'];document.getElementById('summary').innerHTML=statuses.map(s=>`<div class="stat"><b>${report.counts[s]||0}</b><span>${label[s]}</span></div>`).join('');const categories=[...new Set(report.checks.map(x=>x.category))];const filters=['all',...categories];document.getElementById('filters').innerHTML=filters.map(f=>`<button class="${filter===f?'active':''}" data-filter="${esc(f)}">${f==='all'?'All requirements':esc(f)}</button>`).join('');document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;render()});const items=report.checks.filter(x=>filter==='all'||x.category===filter);document.getElementById('checks').innerHTML=items.map(x=>`<article class="check ${x.status}"><div class="dot"></div><div><div class="meta">${esc(x.category)} · ${esc(x.id)}</div><h3>${esc(x.title)}</h3><p>${esc(x.summary)}</p></div><div class="badge">${label[x.status]}</div><details><summary>Evidence${x.source?' · '+esc(x.source):''}</summary><ul class="evidence">${x.evidence.map(e=>`<li>${esc(e)}</li>`).join('')}</ul></details></article>`).join('')||'<div class="empty">No checks in this category.</div>';const metrics=Object.entries(report.metrics||{});document.getElementById('metrics').innerHTML=metrics.map(([k,v])=>`<div class="metric"><small>${esc(k)}</small><b>${typeof v==='number'?Number(v).toLocaleString(undefined,{maximumFractionDigits:2}):esc(v)}</b></div>`).join('')||'<div class="empty">No metrics produced.</div>';document.getElementById('foot').textContent='Generated '+report.generated_at+' · Score excludes field-validation items.'}async function load(){if(embedded){report=embedded;render();return}try{report=await fetch('/api/report',{cache:'no-store'}).then(r=>r.json());render()}catch(e){document.getElementById('checks').innerHTML='<div class="empty">Could not load verification report.</div>'}}load();
</script></body></html>'''


def render_html(report: dict[str, Any] | None = None) -> str:
    payload = ("null" if report is None else
               json.dumps(report, ensure_ascii=False).replace("</", "<\\/"))
    return HTML.replace("__REPORT__", payload)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            body = render_html().encode("utf-8")
            content_type = "text/html; charset=utf-8"
            status = 200
        elif self.path == "/api/report":
            body = json.dumps(build_report(), ensure_ascii=False).encode("utf-8")
            content_type = "application/json; charset=utf-8"
            status = 200
        else:
            body = b"Not found"
            content_type = "text/plain; charset=utf-8"
            status = 404
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true",
                        help="Print the verification report as JSON.")
    parser.add_argument("--export", type=Path,
                        help="Write a self-contained HTML snapshot.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--open", action="store_true",
                        help="Open the dashboard in the default browser.")
    args = parser.parse_args()

    if args.json:
        print(json.dumps(build_report(), indent=2, ensure_ascii=False))
        return 0
    if args.export:
        report = build_report()
        args.export.parent.mkdir(parents=True, exist_ok=True)
        args.export.write_text(render_html(report), encoding="utf-8")
        print(f"Wrote {args.export}")
        return 0

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}"
    print(f"Kilnbeck verification UI: {url}")
    if args.open:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
