"""Deterministic scoring. Pure functions, no I/O, no LLM.

    facts ──▶ dimension lights ──▶ market strength ─┐
                                                     ├──▶ route ──▶ urgency ──▶ partners
    inventory + internal ──▶ health lights ──▶ health ┘

Lights: green / yellow / red / grey. Grey means "not enough dated evidence",
never a default colour. Every light carries a reason string.

Route matrix (health rows, market columns):

                 MARKET STRONG        MARKET MIXED          MARKET WEAK
  HEALTH STRONG  RAISE_GROWTH         SELECTIVE_RAISE       EXTEND_AND_PARTNER
  HEALTH MIXED   OPPORTUNISTIC_RAISE  HOLD_AND_MONITOR      PREPARE_STRATEGIC
  HEALTH WEAK    SELL_OR_BRIDGE       BRIDGE_AND_PROCESS    CONSOLIDATE_OR_EXIT
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta
from statistics import mean

LIGHT_VALUE = {"green": 1.0, "yellow": 0.0, "red": -1.0}
CONF_W = {"high": 1.0, "medium": 0.6, "low": 0.3}
DIR_V = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}
STRONG_CUT, WEAK_CUT = 0.34, -0.34

ROUTES = {
    ("STRONG", "STRONG"): ("RAISE_GROWTH", "Raise from growth funds active in the segment"),
    ("STRONG", "MIXED"): ("SELECTIVE_RAISE", "Raise selectively, lead with traction; market is mixed"),
    ("STRONG", "WEAK"): ("EXTEND_AND_PARTNER", "Extend runway, build a strategic partnership, wait for the window"),
    ("MIXED", "STRONG"): ("OPPORTUNISTIC_RAISE", "Fix the internal gaps fast and raise while the window is open"),
    ("MIXED", "MIXED"): ("HOLD_AND_MONITOR", "Hold, close the data gaps, review next cycle"),
    ("MIXED", "WEAK"): ("PREPARE_STRATEGIC", "Prepare strategic options now; the market will not carry a round"),
    ("WEAK", "STRONG"): ("SELL_OR_BRIDGE", "Sell to a funded peer or bridge to the next milestone; buyers have money"),
    ("WEAK", "MIXED"): ("BRIDGE_AND_PROCESS", "Bridge and start a structured process in parallel"),
    ("WEAK", "WEAK"): ("CONSOLIDATE_OR_EXIT", "Roll-up, consolidation or managed exit. Act now"),
}
ROUTE_WANTS_FUNDS = {"RAISE_GROWTH", "SELECTIVE_RAISE", "OPPORTUNISTIC_RAISE"}
ROUTE_WANTS_BUYERS = {"EXTEND_AND_PARTNER", "PREPARE_STRATEGIC", "SELL_OR_BRIDGE",
                      "BRIDGE_AND_PROCESS", "CONSOLIDATE_OR_EXIT"}


@dataclass
class Light:
    colour: str
    reason: str
    n_facts: int = 0

    def value(self) -> float | None:
        return LIGHT_VALUE.get(self.colour)


def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    s = s.strip()
    for fmt_len, fill in ((10, ""), (7, "-01"), (4, "-01-01")):
        if len(s) == fmt_len:
            try:
                return date.fromisoformat(s + fill)
            except ValueError:
                return None
    return None


def months_ago(as_of: date, months: int) -> date:
    return as_of - timedelta(days=int(months * 30.44))


def recent(items: list[dict], as_of: date, months: int) -> list[dict]:
    floor = months_ago(as_of, months)
    out = []
    for it in items or []:
        d = parse_date(it.get("date"))
        if d is not None and floor <= d <= as_of + timedelta(days=31):
            out.append(it)
    return out


def light_from_facts(facts: list[dict], as_of: date, months: int = 12, min_facts: int = 2) -> Light:
    dated = recent(facts, as_of, months)
    if len(dated) < min_facts:
        return Light("grey", f"{len(dated)} dated facts in the last {months} months (need {min_facts})", len(dated))
    weights = [CONF_W[f["confidence"]] for f in dated]
    score = sum(DIR_V[f["direction"]] * w for f, w in zip(dated, weights)) / sum(weights)
    if score >= 0.3:
        return Light("green", f"net positive ({score:+.2f}) over {len(dated)} dated facts", len(dated))
    if score <= -0.3:
        return Light("red", f"net negative ({score:+.2f}) over {len(dated)} dated facts", len(dated))
    return Light("yellow", f"mixed ({score:+.2f}) over {len(dated)} dated facts", len(dated))


def light_from_count(n: int | None, green_at: int, yellow_at: int, what: str) -> Light:
    if n is None:
        return Light("grey", f"no data on {what}")
    if n >= green_at:
        return Light("green", f"{n} {what} in window", n)
    if n >= yellow_at:
        return Light("yellow", f"{n} {what} in window", n)
    return Light("red", f"0 {what} in window", 0)


def strength(values: list[float]) -> str:
    if not values:
        return "UNKNOWN"
    m = mean(values)
    if m >= STRONG_CUT:
        return "STRONG"
    if m <= WEAK_CUT:
        return "WEAK"
    return "MIXED"


def score_segment(seg: dict | None, as_of: date) -> dict:
    """Five dimension lights and a market strength for one segment. seg=None means the worker failed."""
    if seg is None:
        grey = Light("grey", "segment research unavailable")
        lights = {k: grey for k in ("funding_market", "capital_access", "regulation", "strategics", "exit_comps")}
        return {"lights": {k: asdict(v) for k, v in lights.items()}, "market": "UNKNOWN", "market_value": None}

    lights = {
        "funding_market": light_from_facts(seg["funding_market"]["facts"], as_of, 12),
        "capital_access": light_from_count(len(recent(seg["capital_access"]["active_funds"], as_of, 12)),
                                           3, 1, "active funds"),
        "regulation": light_from_facts(seg["regulation"]["facts"], as_of, 18),
        "strategics": light_from_count(len(recent(seg["strategics"]["players"], as_of, 12)), 2, 1, "vocal strategics"),
        "exit_comps": light_from_count(
            len([d for d in recent(seg["exit_comps"]["deals"], as_of, 24) if d["kind"] != "shutdown"]),
            2, 1, "exit comps"),
    }
    shutdowns = len([d for d in recent(seg["exit_comps"]["deals"], as_of, 24) if d["kind"] == "shutdown"])
    if shutdowns >= 2 and lights["exit_comps"].colour == "green":
        lights["exit_comps"] = Light("yellow", f"{lights['exit_comps'].n_facts} comps but {shutdowns} shutdowns", lights["exit_comps"].n_facts)
    values = [v.value() for v in lights.values() if v.value() is not None]
    return {"lights": {k: asdict(v) for k, v in lights.items()},
            "market": strength(values), "market_value": round(mean(values), 2) if values else None}


def health_lights(inv: dict, internal: dict | None) -> dict[str, Light]:
    internal = internal or {}
    runway = internal.get("runway_months")
    if runway is None:
        rl = Light("grey", "runway not derivable")
    elif runway < 6:
        rl = Light("red", f"runway {runway:.0f} months (as of {internal.get('runway_as_of') or 'n/a'})")
    elif runway < 12:
        rl = Light("yellow", f"runway {runway:.0f} months (as of {internal.get('runway_as_of') or 'n/a'})")
    else:
        rl = Light("green", f"runway {runway:.0f} months (as of {internal.get('runway_as_of') or 'n/a'})")

    band = inv.get("risk_band")
    bl = {"high": Light("red", f"internal risk band high ({inv.get('risk_score')})"),
          "medium": Light("yellow", f"internal risk band medium ({inv.get('risk_score')})"),
          "low": Light("green", f"internal risk band low ({inv.get('risk_score')})")}.get(band, Light("grey", "not ranked"))

    trend = internal.get("kpi_trend", "unknown")
    tl = {"up": Light("green", "KPIs trending up"), "flat": Light("yellow", "KPIs flat"),
          "down": Light("red", "KPIs trending down")}.get(trend, Light("grey", "KPI trend unknown"))

    days = inv.get("days_since_contact")
    if days is None:
        cl = Light("grey", "contact recency unknown")
    elif days > 60:
        cl = Light("red", f"{days} days since founder contact")
    elif days > 30:
        cl = Light("yellow", f"{days} days since founder contact")
    else:
        cl = Light("green", f"{days} days since founder contact")
    return {"runway": rl, "risk_band": bl, "kpi_trend": tl, "contact": cl}


def health_strength(lights: dict[str, Light]) -> str:
    if lights["runway"].colour == "red":
        return "WEAK"
    values = [v.value() for v in lights.values() if v.value() is not None]
    return strength(values)


def pick_route(health: str, market: str, status_override: str | None, active_process: str) -> tuple[str, str]:
    if status_override == "exit_in_progress":
        return "EXIT_IN_PROGRESS", "Exit signed; track closing, earn-out and put-option milestones"
    if active_process == "wind_down":
        return "WIND_DOWN", "Wind-down documented; manage the process"
    h = "MIXED" if health == "UNKNOWN" else health
    m = "MIXED" if market == "UNKNOWN" else market
    return ROUTES[(h, m)]


def urgency(internal: dict | None, health: str, market: str, as_of: date, status_override: str | None) -> tuple[str, str]:
    internal = internal or {}
    runway = internal.get("runway_months")
    deadline = parse_date(internal.get("process_deadline"))
    process = internal.get("active_process", "unknown")
    if status_override == "exit_in_progress":
        return "WATCH", "exit in progress, milestone tracking"
    if runway is not None and runway < 6:
        return "NOW", f"runway {runway:.0f} months"
    if deadline is not None and deadline <= as_of + timedelta(days=60):
        return "NOW", f"documented deadline {deadline.isoformat()}"
    if process in ("m_and_a", "wind_down", "bridge"):
        return "NOW", f"active process: {process}"
    if health == "WEAK" and market == "WEAK":
        return "NOW", "weak company in a weak market"
    if (runway is not None and runway < 12) or health == "WEAK" or market == "WEAK" or process == "fundraise":
        return "QUARTER", "decision needed this quarter"
    return "WATCH", "no trigger"


def partners(route_code: str, seg: dict | None, as_of: date, limit: int = 6) -> list[dict]:
    if seg is None:
        return []
    out: list[dict] = []
    if route_code in ROUTE_WANTS_FUNDS:
        pool = sorted(seg["capital_access"]["active_funds"], key=lambda x: x.get("date") or "", reverse=True)
        out = [{"name": f["name"], "kind": "fund", "evidence": f["evidence"], "date": f["date"], "source_url": f["source_url"]} for f in pool]
    elif route_code in ROUTE_WANTS_BUYERS:
        players = [{"name": p["name"], "kind": "strategic", "evidence": p["evidence"], "date": p["date"], "source_url": p["source_url"]}
                   for p in seg["strategics"]["players"]]
        acquirers = [{"name": d["acquirer_or_lead"], "kind": "acquirer", "evidence": f"{d['kind']} of {d['target']} {d.get('value') or ''}".strip(),
                      "date": d["date"], "source_url": d["source_url"]}
                     for d in seg["exit_comps"]["deals"] if d["kind"] in ("acquisition", "merger")]
        seen, merged = set(), []
        for p in sorted(players + acquirers, key=lambda x: x.get("date") or "", reverse=True):
            key = p["name"].strip().lower()
            if key not in seen:
                seen.add(key)
                merged.append(p)
        out = merged
    return out[:limit]


def score_company(inv: dict, cfg: dict, company_res: dict | None, seg_res: dict | None, seg_score: dict, as_of: date) -> dict:
    internal = (company_res or {}).get("internal")
    hl = health_lights(inv, internal)
    health = health_strength(hl)
    override = cfg.get("status_override")
    route_code, route_label = pick_route(health, seg_score["market"], override, (internal or {}).get("active_process", "unknown"))
    urg, urg_reason = urgency(internal, health, seg_score["market"], as_of, override)
    coverage = list(inv.get("coverage_notes") or [])
    if company_res is None:
        coverage.append("company research unavailable")
    elif internal and internal.get("data_status") != "ok":
        coverage.append(f"internal data status: {internal['data_status']}")
    if seg_res is None:
        coverage.append("segment research unavailable")
    return {
        "company": inv["name"], "org_id": inv.get("org_id"), "segment": cfg["segment"], "funds": inv.get("funds", []),
        "health": health, "health_lights": {k: asdict(v) for k, v in hl.items()},
        "market": seg_score["market"], "market_lights": seg_score["lights"],
        "route": route_code, "route_label": route_label,
        "urgency": urg, "urgency_reason": urg_reason,
        "partners": partners(route_code, seg_res, as_of),
        "internal": internal, "attention_items": inv.get("attention_items", []),
        "external_facts": (company_res or {}).get("external_facts", []),
        "segment_check": (company_res or {}).get("segment_check"),
        "coverage": coverage,
    }


URGENCY_ORDER = {"NOW": 0, "QUARTER": 1, "WATCH": 2}


def score_portfolio(inventory: list[dict], companies_cfg: dict, segment_data: dict[str, dict | None],
                    company_data: dict[str, dict | None], macro: dict | None, as_of: date) -> dict:
    seg_scores = {sid: score_segment(sdata, as_of) for sid, sdata in segment_data.items()}
    rows = []
    for inv in inventory:
        cfg = companies_cfg.get(inv["name"])
        if cfg is None:
            continue
        sid = cfg["segment"]
        rows.append(score_company(inv, cfg, company_data.get(inv["name"]), segment_data.get(sid),
                                  seg_scores.get(sid, score_segment(None, as_of)), as_of))
    rows.sort(key=lambda r: (URGENCY_ORDER[r["urgency"]], -(r["health_lights"]["runway"]["colour"] == "red"), r["company"]))
    return {"as_of": as_of.isoformat(), "macro": macro, "segments": seg_scores, "companies": rows}
