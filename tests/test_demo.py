import json

import run


def test_demo_builds_and_is_labelled(tmp_path):
    assert run.run_demo(tmp_path) == 0
    html = (tmp_path / "index.html").read_text()
    pulse = json.loads((tmp_path / "pulse.json").read_text())
    assert "DEMO DATA" in html and "fictional" in html and "confidential" not in html.lower()
    by = {c["company"]: c for c in pulse["companies"]}
    # the showcase shape: growth cases, roll-ups, an escalation, an exit in progress
    assert by["Helios Ferment"]["recommended_path"] == "growth_round" and by["Helios Ferment"]["paths"]["growth_round"]["colour"] == "green"
    assert any(p["name"] == "Accel" for p in by["Helios Ferment"]["counterparties"]["growth_round"])
    assert any(m["name"] == "Accel" for m in by["Helios Ferment"]["matches"])
    assert by["Nordic Oat Co"]["recommended_path"] == "roll_up"
    assert by["Aquaflow Hydration"]["urgency"] == "ESCALATE"
    assert by["CocoaFree Labs"]["recommended_path"] == "exit_in_progress"
