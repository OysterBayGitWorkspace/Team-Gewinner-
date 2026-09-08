from datetime import date

from pulse import scoring as S

AS_OF = date(2026, 9, 8)


def fact(claim="x", d="2026-06-01", direction="positive", conf="high", url="https://e.x/a"):
    return {"claim": claim, "date": d, "direction": direction, "source_url": url, "source_type": "web", "confidence": conf}


def named(name, d="2026-05-01"):
    return {"name": name, "evidence": "led round", "date": d, "source_url": "https://e.x/f"}


def deal(target, kind="acquisition", d="2026-01-01"):
    return {"target": target, "acquirer_or_lead": "Big Co", "kind": kind, "date": d, "value": None, "source_url": None}


def segment(funding=(), funds=(), reg=(), players=(), deals=()):
    return {"segment_id": "s", "funding_market": {"facts": list(funding)},
            "capital_access": {"facts": [], "active_funds": list(funds)},
            "regulation": {"facts": list(reg)}, "strategics": {"facts": [], "players": list(players)},
            "exit_comps": {"facts": [], "deals": list(deals)}}


def test_parse_date_variants():
    assert S.parse_date("2026-09-08") == date(2026, 9, 8)
    assert S.parse_date("2026-09") == date(2026, 9, 1)
    assert S.parse_date("2026") == date(2026, 1, 1)
    assert S.parse_date("soon") is None
    assert S.parse_date(None) is None


def test_light_grey_when_too_few_dated_facts():
    l = S.light_from_facts([fact(d=None), fact(d="2023-01-01")], AS_OF)
    assert l.colour == "grey"


def test_light_green_red_yellow():
    assert S.light_from_facts([fact(), fact()], AS_OF).colour == "green"
    assert S.light_from_facts([fact(direction="negative"), fact(direction="negative")], AS_OF).colour == "red"
    assert S.light_from_facts([fact(), fact(direction="negative")], AS_OF).colour == "yellow"


def test_confidence_weights_matter():
    # one high-confidence negative (1.0) vs one low positive (0.3): (-1 + 0.3) / 1.3 = -0.54 → red
    assert S.light_from_facts([fact(direction="negative", conf="high"), fact(conf="low")], AS_OF).colour == "red"
    # vs two low positives (0.6): (-1 + 0.6) / 1.6 = -0.25 → yellow, inside the ±0.3 band
    assert S.light_from_facts([fact(direction="negative", conf="high"), fact(conf="low"), fact(conf="low")], AS_OF).colour == "yellow"


def test_count_lights():
    assert S.light_from_count(3, 3, 1, "x").colour == "green"
    assert S.light_from_count(1, 3, 1, "x").colour == "yellow"
    assert S.light_from_count(0, 3, 1, "x").colour == "red"
    assert S.light_from_count(None, 3, 1, "x").colour == "grey"


def test_segment_strong_market():
    seg = segment(funding=[fact(), fact()], funds=[named("A"), named("B"), named("C")], reg=[fact(), fact()],
                  players=[named("X"), named("Y")], deals=[deal("t1"), deal("t2")])
    sc = S.score_segment(seg, AS_OF)
    assert sc["market"] == "STRONG"
    assert all(v["colour"] == "green" for v in sc["lights"].values())


def test_segment_weak_and_shutdown_damping():
    seg = segment(funding=[fact(direction="negative"), fact(direction="negative")], funds=[], reg=[fact(direction="negative"), fact(direction="negative")],
                  players=[], deals=[deal("a"), deal("b"), deal("c", "shutdown"), deal("d", "shutdown")])
    sc = S.score_segment(seg, AS_OF)
    assert sc["lights"]["exit_comps"]["colour"] == "yellow"
    assert sc["market"] == "WEAK"


def test_segment_none_is_all_grey_unknown():
    sc = S.score_segment(None, AS_OF)
    assert sc["market"] == "UNKNOWN" and all(v["colour"] == "grey" for v in sc["lights"].values())


def test_old_evidence_is_ignored():
    seg = segment(funds=[named("A", "2024-01-01")], deals=[deal("t", d="2023-01-01")])
    sc = S.score_segment(seg, AS_OF)
    assert sc["lights"]["capital_access"]["colour"] == "red"
    assert sc["lights"]["exit_comps"]["colour"] == "red"


def inv(name="Co", band="medium", days=10):
    return {"name": name, "org_id": "1", "status": "active", "funds": ["Fund II"], "risk_band": band, "risk_score": 5,
            "days_since_contact": days, "attention_items": ["a"], "coverage_notes": []}


def internal(runway=18.0, trend="up", process="none", deadline=None, status="ok"):
    return {"runway_months": runway, "runway_as_of": "2026-06-30", "cash": "EUR 1m", "cash_as_of": "2026-06-30",
            "kpi_trend": trend, "active_process": process, "process_deadline": deadline, "data_status": status, "notes": []}


def test_health_runway_red_dominates():
    hl = S.health_lights(inv(band="low", days=1), internal(runway=3, trend="up"))
    assert S.health_strength(hl) == "WEAK"


def test_health_strong_and_unknown():
    assert S.health_strength(S.health_lights(inv(band="low", days=5), internal(runway=20, trend="up"))) == "STRONG"
    assert S.health_strength(S.health_lights(inv(band=None, days=None), None)) == "UNKNOWN"


def test_route_matrix_and_overrides():
    assert S.pick_route("STRONG", "STRONG", None, "none")[0] == "RAISE_GROWTH"
    assert S.pick_route("WEAK", "WEAK", None, "none")[0] == "CONSOLIDATE_OR_EXIT"
    assert S.pick_route("WEAK", "STRONG", None, "none")[0] == "SELL_OR_BRIDGE"
    assert S.pick_route("UNKNOWN", "UNKNOWN", None, "unknown")[0] == "HOLD_AND_MONITOR"
    assert S.pick_route("STRONG", "STRONG", "exit_in_progress", "none")[0] == "EXIT_IN_PROGRESS"
    assert S.pick_route("MIXED", "MIXED", None, "wind_down")[0] == "WIND_DOWN"


def test_urgency_triggers():
    assert S.urgency(internal(runway=4), "MIXED", "MIXED", AS_OF, None)[0] == "NOW"
    assert S.urgency(internal(deadline="2026-09-30"), "STRONG", "STRONG", AS_OF, None)[0] == "NOW"
    assert S.urgency(internal(process="m_and_a"), "STRONG", "STRONG", AS_OF, None)[0] == "NOW"
    assert S.urgency(internal(), "WEAK", "WEAK", AS_OF, None)[0] == "NOW"
    assert S.urgency(internal(runway=9), "STRONG", "STRONG", AS_OF, None)[0] == "QUARTER"
    assert S.urgency(internal(process="fundraise"), "STRONG", "STRONG", AS_OF, None)[0] == "QUARTER"
    assert S.urgency(internal(), "STRONG", "STRONG", AS_OF, None)[0] == "WATCH"
    assert S.urgency(internal(runway=2), "WEAK", "WEAK", AS_OF, "exit_in_progress")[0] == "WATCH"
    assert S.urgency(None, "UNKNOWN", "UNKNOWN", AS_OF, None)[0] == "WATCH"


def test_partners_follow_route():
    seg = segment(funds=[named("Growth Fund")], players=[named("Nestlé")], deals=[deal("peer")])
    assert [p["name"] for p in S.partners("RAISE_GROWTH", seg, AS_OF)] == ["Growth Fund"]
    buyers = [p["name"] for p in S.partners("CONSOLIDATE_OR_EXIT", seg, AS_OF)]
    assert "Nestlé" in buyers and "Big Co" in buyers
    assert S.partners("HOLD_AND_MONITOR", seg, AS_OF) == []
    assert S.partners("RAISE_GROWTH", None, AS_OF) == []


def test_score_portfolio_sorts_by_urgency_and_marks_coverage():
    cfg = {"A": {"segment": "s"}, "B": {"segment": "s"}, "Z": {"segment": "s", "status_override": "exit_in_progress"}}
    seg = segment(funding=[fact(), fact()], funds=[named("F1"), named("F2"), named("F3")], reg=[fact(), fact()],
                  players=[named("P1"), named("P2")], deals=[deal("d1"), deal("d2")])
    pulse = S.score_portfolio([inv("A", "low"), inv("B", "high"), inv("Z")], cfg, {"s": seg},
                              {"A": {"internal": internal(runway=20), "external_facts": [], "segment_check": "fits"},
                               "B": {"internal": internal(runway=3, trend="down"), "external_facts": [], "segment_check": "fits"},
                               "Z": None}, None, AS_OF)
    names = [c["company"] for c in pulse["companies"]]
    assert names[0] == "B" and pulse["companies"][0]["urgency"] == "NOW"
    z = next(c for c in pulse["companies"] if c["company"] == "Z")
    assert z["route"] == "EXIT_IN_PROGRESS" and "company research unavailable" in z["coverage"]
    a = next(c for c in pulse["companies"] if c["company"] == "A")
    assert a["route"] == "RAISE_GROWTH" and len(a["partners"]) == 3


def test_replay_is_deterministic():
    seg = segment(funding=[fact(), fact()], funds=[named("F1")])
    args = ([inv("A")], {"A": {"segment": "s"}}, {"s": seg}, {"A": {"internal": internal(), "external_facts": [], "segment_check": "fits"}}, None, AS_OF)
    assert S.score_portfolio(*args) == S.score_portfolio(*args)
