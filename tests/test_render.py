from datetime import date

from pulse import scoring as S
from pulse.render import render_html, render_markdown, slug
from tests.test_scoring import deal, fact, internal, inv, named, segment

AS_OF = date(2026, 9, 8)
SEG_CFG = {"s": {"label": "Seg <b>Label</b>"}}


def build_pulse(with_seg=True):
    seg = segment(funding=[fact(claim="<script>alert(1)</script>" + "x" * 500), fact()], funds=[named("F1")],
                  players=[named("P")], deals=[deal("d")]) if with_seg else None
    return S.score_portfolio([inv("Mühlenkraft")], {"Mühlenkraft": {"segment": "s"}}, {"s": seg},
                             {"Mühlenkraft": {"internal": internal(), "external_facts": [fact(url="javascript:alert(1)")], "segment_check": "fits"}},
                             None, AS_OF), seg


def report(seg):
    return {"run_id": "2026-09-08", "generated_at": "now", "segment_data": {"s": seg},
            "workers": [{"name": "a", "ok": True, "error": None, "error_kind": None, "duration_s": 1.0, "cost_usd": 0.1, "turns": 1},
                        {"name": "b", "ok": False, "error": "x" * 900, "error_kind": "timeout", "duration_s": 400.0, "cost_usd": 0, "turns": 0}]}


def test_html_escapes_and_truncates():
    pulse, seg = build_pulse()
    html = render_html(pulse, report(seg), SEG_CFG)
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "Seg &lt;b&gt;" in html
    assert "javascript:alert" not in html  # non-http URL never becomes a link
    assert "x" * 401 not in html  # truncated
    assert "Mühlenkraft" in html and 'id="c-muhlenkraft"' in html
    assert "1/2 workers succeeded" in html and "warn" in html


def test_html_handles_missing_segment_and_macro():
    pulse, seg = build_pulse(with_seg=False)
    html = render_html(pulse, report(None), SEG_CFG)
    assert "segment research unavailable" in html and "macro research unavailable" in html


def test_markdown_digest():
    pulse, seg = build_pulse()
    md = render_markdown(pulse, report(seg), SEG_CFG)
    assert md.startswith("# Portfolio Market Pulse") and "Mühlenkraft" in md and "1/2 workers" in md


def test_slug():
    assert slug("Löwenzahn Organics") == "lowenzahn-organics"
    assert slug("Air Up") == "air-up"
    assert slug("???") == "x"
