import json

import run


def test_demo_builds_and_is_labelled(tmp_path):
    assert run.run_demo(tmp_path) == 0
    html = (tmp_path / "index.html").read_text()
    pulse = json.loads((tmp_path / "pulse.json").read_text())
    assert "DEMO DATA" in html and "fictional" in html and "confidential" not in html.lower()
    by = {c["company"]: c for c in pulse["companies"]}
    # growth cases point at Accel through real, linked evidence
    for name in ("Verdantis Robotics", "Kitchenetic"):
        assert by[name]["recommended_path"] == "growth_round", name
        assert any(p["name"].startswith("Accel") and (p["source_url"] or "").startswith("http") for p in by[name]["counterparties"]["growth_round"]), name
        assert any(m["name"].startswith("Accel") for m in by[name]["matches"]), name
    # fermentation points at who actually funds it in Europe
    assert any("Bpifrance" in p["name"] for p in by["Helios Ferment"]["counterparties"]["growth_round"])
    # roll-up, escalation, exit in progress
    assert by["Nordic Oat Co"]["recommended_path"] == "roll_up"
    assert any("LIVEKINDLY" in p["name"] for p in by["Nordic Oat Co"]["counterparties"]["roll_up"])
    assert by["Aquaflow Hydration"]["urgency"] == "ESCALATE"
    assert by["CocoaFree Labs"]["recommended_path"] == "exit_in_progress"
    # every market-side link is a real URL; fictional company facts carry none
    for c in pulse["companies"]:
        for path in c["counterparties"].values():
            for p in path:
                assert p["source_url"] is None or p["source_url"].startswith("http")
        assert all(f["source_url"] is None for f in c["external_facts"])
    assert "example.org" not in html
