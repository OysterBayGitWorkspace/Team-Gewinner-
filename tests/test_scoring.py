from datetime import date

from pulse import scoring as S

AS_OF = date(2026, 9, 8)
SEG_CFG = {"s": {"label": "Cultivated meat and cell-ag inputs", "keywords": ["cultivated meat", "cultivated pet food"]}}


def fact(claim="x", d="2026-06-01", direction="positive", conf="high", url="https://e.x/a"):
    return {"claim": claim, "date": d, "direction": direction, "source_url": url, "source_type": "web", "confidence": conf}


def named(name, d="2026-05-01", intent="acted", kw=(), evidence="led round"):
    return {"name": name, "evidence": evidence, "date": d, "source_url": "https://e.x/f", "intent": intent, "mandate_keywords": list(kw)}


def deal(target, kind="acquisition", d="2026-01-01"):
    return {"target": target, "acquirer_or_lead": "Big Co", "kind": kind, "date": d, "value": None, "source_url": None}


def segment(funding=(), funds=(), reg=(), players=(), deals=(), cons=()):
    return {"segment_id": "s", "funding_market": {"facts": list(funding)},
            "capital_access": {"facts": [], "active_funds": list(funds)},
            "regulation": {"facts": list(reg)}, "strategics": {"facts": [], "players": list(players)},
            "exit_comps": {"facts": [], "deals": list(deals)},
            "consolidators": {"facts": [], "players": list(cons)}}


def inv(name="Co", band="medium", days=10):
    return {"name": name, "org_id": "1", "status": "active", "funds": ["Fund II"], "risk_band": band, "risk_score": 5,
            "days_since_contact": days, "attention_items": ["a"], "coverage_notes": []}


def internal(runway=18.0, trend="up", process="none", deadline=None, status="ok", as_of="2026-09-01"):
    return {"runway_months": runway, "runway_as_of": as_of, "cash": "EUR 1m", "cash_as_of": as_of,
            "kpi_trend": trend, "active_process": process, "process_deadline": deadline, "data_status": status, "notes": []}


def test_effective_runway_ages_stale_readings():
    # Dropz case: 3 months as of April, read in September → 0 today → ESCALATE
    r, note = S.effective_runway(internal(runway=3, as_of="2026-04-01"), AS_OF)
    assert r == 0.0 and "aged" in note
    assert S.urgency(internal(runway=3, as_of="2026-04-01"), "WEAK", "STRONG", AS_OF, None)[0] == "ESCALATE"
    # fresh reading is not aged; unknown as-of is not aged
    assert S.effective_runway(internal(runway=3, as_of="2026-08-20"), AS_OF)[0] == 3.0
    assert S.effective_runway(internal(runway=3, as_of=None), AS_OF)[0] == 3.0
    # 21 months as of June → about 18.7 today, still green
    r, _ = S.effective_runway(internal(runway=21.5, as_of="2026-06-30"), AS_OF)
    assert 18 < r < 20


def test_roll_up_label_follows_health_and_watch_prefix():
    only_rollup = {"growth_round": S.Light("yellow", ""), "strategic_ma": S.Light("yellow", ""), "roll_up": S.Light("green", "")}
    assert "acquirer" in S.pick_path(only_rollup, "STRONG", None, "none")[1]
    assert "join a platform" in S.pick_path(only_rollup, "WEAK", None, "none")[1]
    seg = segment(funding=[fact(), fact(direction="negative")], funds=[named("F1"), named("F2"), named("F3")], cons=[named("PE1"), named("PE2")])
    row = S.score_company(inv("A", "low"), {"segment": "s"}, SEG_CFG["s"], company(internal(runway=21)), seg, S.score_segment(seg, AS_OF), AS_OF)
    assert row["urgency"] == "WATCH" and row["health"] == "STRONG"
    assert row["recommended_label"].startswith("No action required.")


def company(int_=None, ext=(), check="fits"):
    return {"internal": int_ if int_ is not None else internal(), "external_facts": list(ext), "segment_check": check}


# ---- dates and primitives ----
def test_parse_date_variants():
    assert S.parse_date("2026-09-08") == date(2026, 9, 8)
    assert S.parse_date("2026-09") == date(2026, 9, 1)
    assert S.parse_date("2026") == date(2026, 1, 1)
    assert S.parse_date("soon") is None and S.parse_date(None) is None


def test_future_dated_items_are_dropped():
    assert S.recent([{"date": "2032-12-31"}, {"date": "2026-08-01"}], AS_OF, 12) == [{"date": "2026-08-01"}]


def test_light_grey_when_too_few_dated_facts():
    assert S.light_from_facts([fact(d=None), fact(d="2023-01-01")], AS_OF, 12).colour == "grey"


def test_light_green_red_yellow_and_weights():
    assert S.light_from_facts([fact(), fact()], AS_OF, 12).colour == "green"
    assert S.light_from_facts([fact(direction="negative"), fact(direction="negative")], AS_OF, 12).colour == "red"
    assert S.light_from_facts([fact(), fact(direction="negative")], AS_OF, 12).colour == "yellow"
    assert S.light_from_facts([fact(direction="negative", conf="high"), fact(conf="low")], AS_OF, 12).colour == "red"
    assert S.light_from_facts([fact(direction="negative", conf="high"), fact(conf="low"), fact(conf="low")], AS_OF, 12).colour == "yellow"


def test_count_lights():
    assert S.light_from_count(3, 3, 1, "x").colour == "green"
    assert S.light_from_count(1, 3, 1, "x").colour == "yellow"
    assert S.light_from_count(0, 3, 1, "x").colour == "red"
    assert S.light_from_count(None, 3, 1, "x").colour == "grey"


# ---- segment ----
def strong_segment():
    return segment(funding=[fact(), fact()], funds=[named("A"), named("B"), named("C")], reg=[fact(), fact()],
                   players=[named("X"), named("Y")], deals=[deal("t1"), deal("t2")], cons=[named("PE1"), named("PE2")])


def test_segment_strong_market_six_lights():
    sc = S.score_segment(strong_segment(), AS_OF)
    assert sc["market"] == "STRONG" and len(sc["lights"]) == 6
    assert all(v["colour"] == "green" for v in sc["lights"].values())


def test_segment_weak_and_shutdown_damping():
    seg = segment(funding=[fact(direction="negative"), fact(direction="negative")], reg=[fact(direction="negative"), fact(direction="negative")],
                  deals=[deal("a"), deal("b"), deal("c", "shutdown"), deal("d", "shutdown")])
    sc = S.score_segment(seg, AS_OF)
    assert sc["lights"]["exit_comps"]["colour"] == "yellow" and sc["lights"]["consolidators"]["colour"] == "red"
    assert sc["market"] == "WEAK"


def test_segment_none_is_all_grey_unknown():
    sc = S.score_segment(None, AS_OF)
    assert sc["market"] == "UNKNOWN" and all(v["colour"] == "grey" for v in sc["lights"].values())


def test_old_evidence_is_ignored():
    sc = S.score_segment(segment(funds=[named("A", "2024-01-01")], deals=[deal("t", d="2023-01-01")]), AS_OF)
    assert sc["lights"]["capital_access"]["colour"] == "red" and sc["lights"]["exit_comps"]["colour"] == "red"


# ---- health ----
def test_health_is_weighted_not_overridden():
    # runway red (3 months) but everything else green: weighted mean = (-2 + 1.5 + 1.5 + 0.5 + 1) / 6.5 = +0.38 → STRONG
    hl = S.health_lights(inv(band="low", days=1), internal(runway=3, trend="up"), [fact(), fact()], AS_OF)
    assert hl["runway"]["colour"] if isinstance(hl["runway"], dict) else hl["runway"].colour == "red"
    assert S.health_strength(hl) == "STRONG"


def test_health_momentum_light_from_own_news():
    hl = S.health_lights(inv(), internal(), [fact(direction="negative"), fact(direction="negative")], AS_OF)
    assert hl["momentum"].colour == "red" and hl["momentum"].reason.startswith("own news")
    assert S.health_lights(inv(), internal(), [], AS_OF)["momentum"].colour == "grey"


def test_health_unknown_when_nothing():
    assert S.health_strength(S.health_lights(inv(band=None, days=None), None, [], AS_OF)) == "UNKNOWN"


# ---- paths ----
def L(**colours):
    base = {k: {"colour": "yellow", "reason": ""} for k in ("funding_market", "capital_access", "regulation", "strategics", "exit_comps", "consolidators")}
    for k, v in colours.items():
        base[k] = {"colour": v, "reason": ""}
    return base


def test_path_lights_rules():
    p = S.path_lights(L(capital_access="green", funding_market="green", strategics="green", exit_comps="green", consolidators="green"), "STRONG")
    assert {k: v.colour for k, v in p.items()} == {"growth_round": "green", "strategic_ma": "green", "roll_up": "green"}
    p = S.path_lights(L(capital_access="green", funding_market="green"), "MIXED")
    assert p["growth_round"].colour == "yellow"
    p = S.path_lights(L(capital_access="green", funding_market="green"), "WEAK")
    assert p["growth_round"].colour == "red"
    p = S.path_lights(L(strategics="red", exit_comps="red", consolidators="red"), "STRONG")
    assert p["strategic_ma"].colour == "red" and p["roll_up"].colour == "red"
    p = S.path_lights(L(consolidators="grey"), "STRONG")
    assert p["roll_up"].colour == "yellow" and "grey counted as yellow" in p["roll_up"].reason


def test_pick_path_preference_and_overrides():
    g = {"growth_round": S.Light("green", ""), "strategic_ma": S.Light("green", ""), "roll_up": S.Light("yellow", "")}
    assert S.pick_path(g, "STRONG", None, "none")[0] == "growth_round"
    assert S.pick_path(g, "WEAK", None, "none")[0] == "strategic_ma"
    r = {k: S.Light("red", "") for k in g}
    assert S.pick_path(r, "MIXED", None, "none")[0] == "bridge_and_process"
    assert S.pick_path(g, "STRONG", "exit_in_progress", "none")[0] == "exit_in_progress"
    assert S.pick_path(g, "STRONG", None, "wind_down")[0] == "wind_down"
    only_rollup = {"growth_round": S.Light("red", ""), "strategic_ma": S.Light("red", ""), "roll_up": S.Light("yellow", "")}
    assert S.pick_path(only_rollup, "WEAK", None, "none")[0] == "roll_up"


# ---- urgency ----
def test_urgency_tiers():
    assert S.urgency(internal(runway=1.5), "STRONG", "STRONG", AS_OF, None)[0] == "ESCALATE"   # 6.5 weeks
    assert S.urgency(internal(runway=2.0), "STRONG", "STRONG", AS_OF, None)[0] == "NOW"        # 8.7 weeks
    assert S.urgency(internal(runway=4), "MIXED", "MIXED", AS_OF, None)[0] == "NOW"
    assert S.urgency(internal(deadline="2026-09-30"), "STRONG", "STRONG", AS_OF, None)[0] == "NOW"
    assert S.urgency(internal(process="m_and_a"), "STRONG", "STRONG", AS_OF, None)[0] == "NOW"
    assert S.urgency(internal(), "WEAK", "WEAK", AS_OF, None)[0] == "NOW"
    assert S.urgency(internal(runway=9), "STRONG", "STRONG", AS_OF, None)[0] == "QUARTER"
    assert S.urgency(internal(process="fundraise"), "STRONG", "STRONG", AS_OF, None)[0] == "QUARTER"
    assert S.urgency(internal(), "STRONG", "STRONG", AS_OF, None)[0] == "WATCH"
    assert S.urgency(internal(runway=1), "WEAK", "WEAK", AS_OF, "exit_in_progress")[0] == "WATCH"
    assert S.urgency(None, "UNKNOWN", "UNKNOWN", AS_OF, None)[0] == "WATCH"


# ---- counterparties and lid-to-pot ----
def test_counterparties_per_path():
    seg = segment(funds=[named("Growth Fund")], players=[named("Nestlé")], deals=[deal("peer")], cons=[named("BuyBuild PE")])
    cp = S.counterparties(seg)
    assert [p["name"] for p in cp["growth_round"]] == ["Growth Fund"]
    assert {p["name"] for p in cp["strategic_ma"]} == {"Nestlé", "Big Co"}
    assert [p["name"] for p in cp["roll_up"]] == ["BuyBuild PE"]
    assert S.counterparties(None) == {"growth_round": [], "strategic_ma": [], "roll_up": []}


def test_lid_to_pot_matches_stated_intent_only():
    seg = segment(funds=[named("Acted Fund", intent="acted", kw=["cultivated meat"]),
                         named("Mandate Fund", intent="stated_looking_for", kw=["cultivated meat", "pet food"], evidence="closed $200m fund for cultivated meat"),
                         named("Other Fund", intent="stated_looking_for", kw=["fintech", "payments"]),
                         named("Old Fund", d="2024-01-01", intent="stated_looking_for", kw=["cultivated meat"])],
                  players=[named("Mars Petcare", intent="stated_looking_for", kw=["cultivated pet food"], evidence="looking for cultivated pet food partners")])
    m = S.lid_to_pot(seg, SEG_CFG["s"], "Cultivated chicken for pet food", AS_OF)
    names = [x["name"] for x in m]
    assert "Mandate Fund" in names and "Mars Petcare" in names
    assert "Acted Fund" not in names and "Other Fund" not in names and "Old Fund" not in names
    assert m[0]["match_score"] >= m[-1]["match_score"] and all(x["match_terms"] for x in m)


# ---- portfolio ----
def test_score_portfolio_sorts_by_urgency_and_marks_coverage():
    cfg = {"A": {"segment": "s"}, "B": {"segment": "s"}, "Z": {"segment": "s", "status_override": "exit_in_progress"}, "E": {"segment": "s"}}
    seg = strong_segment()
    pulse = S.score_portfolio([inv("A", "low"), inv("B", "high"), inv("Z"), inv("E")], cfg, SEG_CFG, {"s": seg},
                              {"A": company(internal(runway=20)), "B": company(internal(runway=3, trend="down")),
                               "Z": None, "E": company(internal(runway=1.0))}, None, AS_OF)
    names = [c["company"] for c in pulse["companies"]]
    assert names[:2] == ["E", "B"]
    assert pulse["companies"][0]["urgency"] == "ESCALATE" and pulse["companies"][1]["urgency"] == "NOW"
    z = next(c for c in pulse["companies"] if c["company"] == "Z")
    assert z["recommended_path"] == "exit_in_progress" and "company research unavailable" in z["coverage"]
    a = next(c for c in pulse["companies"] if c["company"] == "A")
    assert a["recommended_path"] == "growth_round" and len(a["counterparties"]["growth_round"]) == 3
    assert set(a["paths"]) == {"growth_round", "strategic_ma", "roll_up"}


def test_replay_is_deterministic():
    args = ([inv("A")], {"A": {"segment": "s"}}, SEG_CFG, {"s": strong_segment()}, {"A": company()}, None, AS_OF)
    assert S.score_portfolio(*args) == S.score_portfolio(*args)
