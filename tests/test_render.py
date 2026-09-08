from datetime import date

from pulse import scoring as S
from pulse.render import render_html, render_markdown, slug
from tests.test_scoring import SEG_CFG, company, deal, fact, internal, inv, named, segment

AS_OF = date(2026, 9, 8)
CFG = {"s": {"label": "Seg <b>Label</b>", "keywords": ["cultivated meat"]}}


def build_pulse(with_seg=True):
    seg = segment(funding=[fact(claim="<script>alert(1)</script>" + "x" * 500), fact()], funds=[named("F1")],
                  players=[named("P", intent="stated_looking_for", kw=["cultivated meat"], evidence="we look for cultivated meat")],
                  deals=[deal("d")], cons=[named("PE")]) if with_seg else None
    pulse = S.score_portfolio([inv("Mühlenkraft")], {"Mühlenkraft": {"segment": "s", "one_liner": "cultivated meat snacks"}}, CFG, {"s": seg},
                              {"Mühlenkraft": company(internal(), [fact(url="javascript:alert(1)")])}, None, AS_OF)
    return pulse, seg


def report(seg):
    return {"run_id": "2026-09-08", "generated_at": "now", "segment_data": {"s": seg},
            "workers": [{"name": "a", "ok": True, "error": None, "error_kind": None, "duration_s": 1.0, "cost_usd": 0.1, "turns": 1},
                        {"name": "b", "ok": False, "error": "x" * 900, "error_kind": "timeout", "duration_s": 400.0, "cost_usd": 0, "turns": 0}]}


def test_html_escapes_and_truncates():
    pulse, seg = build_pulse()
    html = render_html(pulse, report(seg), CFG)
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "Seg &lt;b&gt;" in html
    assert "javascript:alert" not in html
    assert "x" * 401 not in html
    assert "Mühlenkraft" in html and 'id="c-muhlenkraft"' in html and 'id="p-muhlenkraft"' in html
    assert "1/2 workers succeeded" in html and "warn" in html
    assert "Lid to pot" in html and "Roll-up / consolidation" in html and "recommended" in html


def test_html_handles_missing_segment_and_macro():
    pulse, seg = build_pulse(with_seg=False)
    html = render_html(pulse, report(None), CFG)
    assert "segment research unavailable" in html and "macro research unavailable" in html
    assert "no dated counterparties found" in html


def test_markdown_digest():
    pulse, seg = build_pulse()
    md = render_markdown(pulse, report(seg), CFG)
    assert md.startswith("# Portfolio Market Pulse") and "Mühlenkraft" in md and "1/2 workers" in md and "Paths:" in md


def test_artifact_body_strips_skeleton():
    from pulse.render import artifact_body
    pulse, seg = build_pulse()
    body = artifact_body(render_html(pulse, report(seg), CFG))
    assert body.startswith("<title>") and "<style>" in body and "Mühlenkraft" in body
    assert "<!DOCTYPE" not in body and "<html" not in body and "<body>" not in body and "<head>" not in body


def test_names_without_source_fall_back_to_search_but_facts_do_not():
    from pulse.render import link
    assert 'google.com/search?q=Bayer+Crop+Science' in link(None, "Bayer Crop Science", fallback_query="Bayer Crop Science")
    assert 'rel="noopener noreferrer"' in link("https://x.y/z", "t") and 'target="_blank"' in link("https://x.y/z", "t")
    assert link(None, "plain") == "plain"
    pulse, seg = build_pulse()
    html = render_html(pulse, report(seg), CFG)
    # internal (fictional/confidential) facts never become search links
    assert html.count("google.com/search") == html.count('class="search-link"')


def test_slug():
    assert slug("Löwenzahn Organics") == "lowenzahn-organics"
    assert slug("Air Up") == "air-up"
    assert slug("???") == "x"
