"""Deterministic scoring. Pure functions, no I/O, no LLM.

    segment facts ──▶ 6 market lights ──▶ market strength ─┐
                                                            ├──▶ 3 path lights ──▶ recommended path
    inventory + internal + own news ──▶ 5 health lights ──▶ health strength ─┘        │
                                                                                      ▼
                                                              urgency (ESCALATE / NOW / QUARTER / WATCH)
                                                              counterparties per path + lid-to-pot matches

Lights: green / yellow / red / grey. Grey means "not enough dated evidence",
never a default colour. Every light carries the rule that produced it.

Paths (one light each, shown side by side on the card):
  growth_round  needs capital access + funding market + company health
  strategic_ma  needs vocal strategics + exit comps
  roll_up       needs consolidators active in the segment
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from statistics import mean

# ---- thresholds, all in one place -------------------------------------------------------------
LIGHT_VALUE = {"green": 1.0, "yellow": 0.0, "red": -1.0}
LIGHT_RANK = {"green": 3, "yellow": 2, "grey": 1, "red": 0}
CONF_W = {"high": 1.0, "medium": 0.6, "low": 0.3}
DIR_V = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}
STRONG_CUT, WEAK_CUT = 0.34, -0.34
FACT_NET_CUT = 0.3
MIN_DATED_FACTS = 2
WINDOW_MONTHS = {"funding_market": 12, "capital_access": 12, "regulation": 18, "strategics": 12,
                 "exit_comps": 24, "consolidators": 24, "momentum": 12}
COUNT_BARS = {  # (green_at, yellow_at)
    "capital_access": (3, 1), "strategics": (2, 1), "exit_comps": (2, 1), "consolidators": (2, 1)}
HEALTH_WEIGHTS = {"runway": 2.0, "risk_band": 1.5, "kpi_trend": 1.5, "contact": 0.5, "momentum": 1.0}
ESCALATE_RUNWAY_WEEKS = 8
RUNWAY_RED_MONTHS, RUNWAY_YELLOW_MONTHS = 6, 12
CONTACT_RED_DAYS, CONTACT_YELLOW_DAYS = 60, 30
WEEKS_PER_MONTH = 4.345

PATH_LABELS = {
    "growth_round": "Follow-on / growth round",
    "strategic_ma": "Strategic M&A",
    "roll_up": "Roll-up / consolidation",
    "bridge_and_process": "Bridge and prepare a structured process",
    "exit_in_progress": "Exit signed: track closing, earn-out and put-option milestones",
    "wind_down": "Wind-down documented: manage the process",
}
PATH_PREFERENCE = {  # tie-break order by company health
    "STRONG": ["growth_round", "strategic_ma", "roll_up"],
    "MIXED": ["growth_round", "strategic_ma", "roll_up"],
    "UNKNOWN": ["growth_round", "strategic_ma", "roll_up"],
    "WEAK": ["strategic_ma", "roll_up", "growth_round"],
}
URGENCY_ORDER = {"ESCALATE": 0, "NOW": 1, "QUARTER": 2, "WATCH": 3}


@dataclass
class Light:
    colour: str
    reason: str
    n: int = 0

    def value(self) -> float | None:
        return LIGHT_VALUE.get(self.colour)


# ---- dates -------------------------------------------------------------------------------------
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


def recent(items: list[dict] | None, as_of: date, months: int) -> list[dict]:
    """Items with a parseable date inside the window. Future-dated items (beyond 31 days) are dropped:
    Jarvis carries contract milestones dated 2032 that must never count as current evidence."""
    floor = months_ago(as_of, months)
    out = []
    for it in items or []:
        d = parse_date(it.get("date"))
        if d is not None and floor <= d <= as_of + timedelta(days=31):
            out.append(it)
    return out


# ---- primitive lights --------------------------------------------------------------------------
def light_from_facts(facts: list[dict], as_of: date, months: int, min_facts: int = MIN_DATED_FACTS) -> Light:
    dated = recent(facts, as_of, months)
    if len(dated) < min_facts:
        return Light("grey", f"{len(dated)} dated facts in the last {months} months (need {min_facts})", len(dated))
    weights = [CONF_W[f["confidence"]] for f in dated]
    score = sum(DIR_V[f["direction"]] * w for f, w in zip(dated, weights)) / sum(weights)
    if score >= FACT_NET_CUT:
        return Light("green", f"net positive ({score:+.2f}) over {len(dated)} dated facts", len(dated))
    if score <= -FACT_NET_CUT:
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


def strength(values: list[float], weights: list[float] | None = None) -> str:
    if not values:
        return "UNKNOWN"
    if weights:
        m = sum(v * w for v, w in zip(values, weights)) / sum(weights)
    else:
        m = mean(values)
    if m >= STRONG_CUT:
        return "STRONG"
    if m <= WEAK_CUT:
        return "WEAK"
    return "MIXED"


def _as_feasibility(colour: str) -> str:
    """Grey counts as yellow for path feasibility (unknown is not a veto), but is flagged by the caller."""
    return "yellow" if colour == "grey" else colour


# ---- segment -----------------------------------------------------------------------------------
def score_segment(seg: dict | None, as_of: date) -> dict:
    dims = ("funding_market", "capital_access", "regulation", "strategics", "exit_comps", "consolidators")
    if seg is None:
        grey = Light("grey", "segment research unavailable")
        return {"lights": {k: asdict(grey) for k in dims}, "market": "UNKNOWN", "market_value": None}

    W = WINDOW_MONTHS
    lights = {
        "funding_market": light_from_facts(seg["funding_market"]["facts"], as_of, W["funding_market"]),
        "capital_access": light_from_count(len(recent(seg["capital_access"]["active_funds"], as_of, W["capital_access"])),
                                           *COUNT_BARS["capital_access"], "active funds"),
        "regulation": light_from_facts(seg["regulation"]["facts"], as_of, W["regulation"]),
        "strategics": light_from_count(len(recent(seg["strategics"]["players"], as_of, W["strategics"])),
                                       *COUNT_BARS["strategics"], "vocal strategics"),
        "exit_comps": light_from_count(
            len([d for d in recent(seg["exit_comps"]["deals"], as_of, W["exit_comps"]) if d["kind"] != "shutdown"]),
            *COUNT_BARS["exit_comps"], "exit comps"),
        "consolidators": light_from_count(len(recent(seg.get("consolidators", {}).get("players", []), as_of, W["consolidators"])),
                                          *COUNT_BARS["consolidators"], "active consolidators"),
    }
    shutdowns = len([d for d in recent(seg["exit_comps"]["deals"], as_of, W["exit_comps"]) if d["kind"] == "shutdown"])
    if shutdowns >= 2 and lights["exit_comps"].colour == "green":
        lights["exit_comps"] = Light("yellow", f"{lights['exit_comps'].n} comps but {shutdowns} shutdowns", lights["exit_comps"].n)
    values = [v.value() for v in lights.values() if v.value() is not None]
    return {"lights": {k: asdict(v) for k, v in lights.items()},
            "market": strength(values), "market_value": round(mean(values), 2) if values else None}


# ---- company health ----------------------------------------------------------------------------
def health_lights(inv: dict, internal: dict | None, external_facts: list[dict] | None, as_of: date) -> dict[str, Light]:
    internal = internal or {}
    runway = internal.get("runway_months")
    ras = internal.get("runway_as_of") or "n/a"
    if runway is None:
        rl = Light("grey", "runway not derivable")
    elif runway < RUNWAY_RED_MONTHS:
        rl = Light("red", f"runway {runway:.1f} months (as of {ras})")
    elif runway < RUNWAY_YELLOW_MONTHS:
        rl = Light("yellow", f"runway {runway:.1f} months (as of {ras})")
    else:
        rl = Light("green", f"runway {runway:.1f} months (as of {ras})")

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
    elif days > CONTACT_RED_DAYS:
        cl = Light("red", f"{days} days since founder contact")
    elif days > CONTACT_YELLOW_DAYS:
        cl = Light("yellow", f"{days} days since founder contact")
    else:
        cl = Light("green", f"{days} days since founder contact")

    ml = light_from_facts(external_facts or [], as_of, WINDOW_MONTHS["momentum"])
    ml.reason = "own news: " + ml.reason
    return {"runway": rl, "risk_band": bl, "kpi_trend": tl, "contact": cl, "momentum": ml}


def health_strength(lights: dict[str, Light]) -> str:
    pairs = [(v.value(), HEALTH_WEIGHTS[k]) for k, v in lights.items() if v.value() is not None]
    if not pairs:
        return "UNKNOWN"
    return strength([p[0] for p in pairs], [p[1] for p in pairs])


def runway_weeks(internal: dict | None) -> float | None:
    r = (internal or {}).get("runway_months")
    return None if r is None else r * WEEKS_PER_MONTH


# ---- paths -------------------------------------------------------------------------------------
def path_lights(seg_lights: dict[str, dict], health: str) -> dict[str, Light]:
    c = {k: seg_lights[k]["colour"] for k in seg_lights}
    flagged = [k for k, v in c.items() if v == "grey"]
    f = {k: _as_feasibility(v) for k, v in c.items()}
    note = f" (grey counted as yellow: {', '.join(flagged)})" if flagged else ""

    ca, fm = f["capital_access"], f["funding_market"]
    if ca == "green" and fm == "green" and health == "STRONG":
        g = Light("green", "capital access and funding market green, company STRONG" + note)
    elif ca in ("green", "yellow") and fm in ("green", "yellow") and health != "WEAK":
        g = Light("yellow", f"capital access {ca}, funding market {fm}, company {health}" + note)
    else:
        g = Light("red", f"capital access {ca}, funding market {fm}, company {health}" + note)

    st, ex = f["strategics"], f["exit_comps"]
    if st == "green" and ex == "green":
        m = Light("green", "vocal strategics and exit comps both green" + note)
    elif st in ("green", "yellow") or ex in ("green", "yellow"):
        m = Light("yellow", f"strategics {st}, exit comps {ex}" + note)
    else:
        m = Light("red", "no vocal strategics and no exit comps in window" + note)

    co = f["consolidators"]
    r = Light(co, f"consolidators light {c['consolidators']}" + note)
    return {"growth_round": g, "strategic_ma": m, "roll_up": r}


def pick_path(paths: dict[str, Light], health: str, status_override: str | None, active_process: str) -> tuple[str, str]:
    if status_override == "exit_in_progress":
        return "exit_in_progress", PATH_LABELS["exit_in_progress"]
    if active_process == "wind_down":
        return "wind_down", PATH_LABELS["wind_down"]
    best_rank = max(LIGHT_RANK[p.colour] for p in paths.values())
    if best_rank == LIGHT_RANK["red"]:
        return "bridge_and_process", PATH_LABELS["bridge_and_process"]
    for key in PATH_PREFERENCE.get(health, PATH_PREFERENCE["MIXED"]):
        if LIGHT_RANK[paths[key].colour] == best_rank:
            return key, PATH_LABELS[key]
    raise AssertionError("unreachable")


# ---- urgency -----------------------------------------------------------------------------------
def urgency(internal: dict | None, health: str, market: str, as_of: date, status_override: str | None) -> tuple[str, str]:
    internal = internal or {}
    runway = internal.get("runway_months")
    weeks = runway_weeks(internal)
    deadline = parse_date(internal.get("process_deadline"))
    process = internal.get("active_process", "unknown")
    if status_override == "exit_in_progress":
        return "WATCH", "exit in progress, milestone tracking"
    if weeks is not None and weeks < ESCALATE_RUNWAY_WEEKS:
        return "ESCALATE", f"runway {weeks:.0f} weeks: find a solution immediately"
    if runway is not None and runway < RUNWAY_RED_MONTHS:
        return "NOW", f"runway {runway:.1f} months"
    if deadline is not None and deadline <= as_of + timedelta(days=60):
        return "NOW", f"documented deadline {deadline.isoformat()}"
    if process in ("m_and_a", "wind_down", "bridge"):
        return "NOW", f"active process: {process}"
    if health == "WEAK" and market == "WEAK":
        return "NOW", "weak company in a weak market"
    if (runway is not None and runway < RUNWAY_YELLOW_MONTHS) or health == "WEAK" or market == "WEAK" or process == "fundraise":
        return "QUARTER", "decision needed this quarter"
    return "WATCH", "no trigger"


# ---- counterparties and lid-to-pot matches -----------------------------------------------------
def _named(items: list[dict], kind: str) -> list[dict]:
    return [{"name": p["name"], "kind": kind, "evidence": p.get("evidence"), "date": p.get("date"),
             "source_url": p.get("source_url"), "intent": p.get("intent"), "mandate_keywords": p.get("mandate_keywords") or []}
            for p in items or []]


def _dedupe(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for p in sorted(items, key=lambda x: x.get("date") or "", reverse=True):
        key = (p["name"] or "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(p)
    return out


def counterparties(seg: dict | None, limit: int = 6) -> dict[str, list[dict]]:
    if seg is None:
        return {"growth_round": [], "strategic_ma": [], "roll_up": []}
    funds = _named(seg["capital_access"]["active_funds"], "fund")
    players = _named(seg["strategics"]["players"], "strategic")
    acquirers = [{"name": d["acquirer_or_lead"], "kind": "acquirer", "evidence": f"{d['kind']} of {d['target']} {d.get('value') or ''}".strip(),
                  "date": d["date"], "source_url": d["source_url"], "intent": "acted", "mandate_keywords": []}
                 for d in seg["exit_comps"]["deals"] if d["kind"] in ("acquisition", "merger")]
    cons = _named(seg.get("consolidators", {}).get("players", []), "consolidator")
    return {"growth_round": _dedupe(funds)[:limit],
            "strategic_ma": _dedupe(players + acquirers)[:limit],
            "roll_up": _dedupe(cons)[:limit]}


_TOKEN = re.compile(r"[a-zäöüß][a-zäöüß0-9-]{3,}")
STOP = {"startup", "startups", "company", "companies", "funding", "food", "agri", "agtech", "foodtech", "europe", "european",
        "platform", "technology", "market", "brand", "brands", "based", "with", "from", "that", "this", "their"}


def _tokens(*texts: str) -> set[str]:
    out: set[str] = set()
    for t in texts:
        out |= {w for w in _TOKEN.findall((t or "").lower()) if w not in STOP}
    return out


def lid_to_pot(seg: dict | None, seg_cfg: dict, one_liner: str, as_of: date, limit: int = 5) -> list[dict]:
    """Demand signals that explicitly say what they look for, ranked by keyword overlap with this company.
    Deterministic: overlap count between the party's mandate keywords and segment keywords + company one-liner."""
    if seg is None:
        return []
    target = _tokens(seg_cfg.get("label", ""), " ".join(seg_cfg.get("keywords") or []), one_liner)
    pool = (_named(seg["capital_access"]["active_funds"], "fund") + _named(seg["strategics"]["players"], "strategic")
            + _named(seg.get("consolidators", {}).get("players", []), "consolidator"))
    out = []
    for p in recent(pool, as_of, 12):
        if p.get("intent") != "stated_looking_for":
            continue
        hits = sorted(_tokens(" ".join(p["mandate_keywords"]), p.get("evidence") or "") & target)
        if hits:
            out.append({**p, "match_score": len(hits), "match_terms": hits[:6]})
    out.sort(key=lambda x: (-x["match_score"], x.get("date") or ""), reverse=False)
    return out[:limit]


# ---- company -----------------------------------------------------------------------------------
def score_company(inv: dict, cfg: dict, seg_cfg: dict, company_res: dict | None, seg_res: dict | None,
                  seg_score: dict, as_of: date) -> dict:
    internal = (company_res or {}).get("internal")
    ext = (company_res or {}).get("external_facts", [])
    hl = health_lights(inv, internal, ext, as_of)
    health = health_strength(hl)
    override = cfg.get("status_override")
    paths = path_lights(seg_score["lights"], health)
    path_key, path_label = pick_path(paths, health, override, (internal or {}).get("active_process", "unknown"))
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
        "paths": {k: asdict(v) for k, v in paths.items()},
        "recommended_path": path_key, "recommended_label": path_label,
        "urgency": urg, "urgency_reason": urg_reason,
        "counterparties": counterparties(seg_res),
        "matches": lid_to_pot(seg_res, seg_cfg, cfg.get("one_liner", ""), as_of),
        "internal": internal, "attention_items": inv.get("attention_items", []),
        "external_facts": ext, "segment_check": (company_res or {}).get("segment_check"),
        "coverage": coverage,
    }


def score_portfolio(inventory: list[dict], companies_cfg: dict, segments_cfg: dict, segment_data: dict[str, dict | None],
                    company_data: dict[str, dict | None], macro: dict | None, as_of: date) -> dict:
    seg_scores = {sid: score_segment(sdata, as_of) for sid, sdata in segment_data.items()}
    rows = []
    for inv in inventory:
        cfg = companies_cfg.get(inv["name"])
        if cfg is None:
            continue
        sid = cfg["segment"]
        rows.append(score_company(inv, cfg, segments_cfg.get(sid, {}), company_data.get(inv["name"]), segment_data.get(sid),
                                  seg_scores.get(sid, score_segment(None, as_of)), as_of))
    rows.sort(key=lambda r: (URGENCY_ORDER[r["urgency"]], -(r["health_lights"]["runway"]["colour"] == "red"), r["company"]))
    return {"as_of": as_of.isoformat(), "macro": macro, "segments": seg_scores, "companies": rows}
