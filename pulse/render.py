"""Render the scored pulse to a single-file HTML dashboard (OB CI) and a Markdown digest.

Everything from workers is untrusted text: every string goes through esc().
Long strings are truncated at render time (see the Slack 3000-char lesson).
"""
from __future__ import annotations

import html
import re
import unicodedata
from datetime import datetime

MAX_TEXT = 400
CSS = r"""@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
:root{--bg0:#f4f6f8;--bg1:#d9dee4;--bg2:#c3cad2;--ink:#0f141a;--ink2:#3d4752;--mute:#6b7683;--line:rgba(15,20,26,.08);--glass:rgba(255,255,255,.62);--glass2:rgba(255,255,255,.85);--graphite:#14181e;--silver:#e6eaee;--green:#22c55e;--amber:#f5b301;--red:#ef4444;--grey:#9aa4ae;--accent:#38bdf8}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{font-family:'Manrope','Inter',system-ui,sans-serif;background:radial-gradient(1200px 600px at 15% -10%,#ffffff 0%,transparent 60%),radial-gradient(900px 500px at 100% 20%,#e9edf1 0%,transparent 55%),linear-gradient(160deg,var(--bg0) 0%,var(--bg1) 55%,var(--bg2) 100%);background-attachment:fixed;color:var(--ink);line-height:1.5;-webkit-font-smoothing:antialiased;min-height:100vh}
h1,h2,h3{font-weight:600;letter-spacing:-0.02em;line-height:1.05}
h1{font-size:clamp(2.2rem,4.5vw,3.8rem);background:linear-gradient(90deg,#ffffff 0%,#c9d1da 60%,#8f9ba7 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
h2{font-size:clamp(1.4rem,2.6vw,2rem);margin-bottom:22px;color:var(--ink)}
h3{font-size:1.35rem} h4{font-weight:600;font-size:.72rem;text-transform:uppercase;letter-spacing:.12em;margin:18px 0 8px;color:var(--mute)}
.container{max-width:1280px;margin:0 auto;padding:0 clamp(20px,3vw,48px)}
.header{background:radial-gradient(800px 300px at 80% 0%,rgba(56,189,248,.18),transparent 60%),linear-gradient(135deg,#0b0f14 0%,#1a2129 60%,#232b34 100%);color:var(--silver);padding:clamp(32px,4vw,64px) 0 clamp(28px,3vw,48px);position:relative;overflow:hidden}
.header::after{content:"";position:absolute;inset:auto -10% -60% -10%;height:120px;background:radial-gradient(closest-side,rgba(255,255,255,.08),transparent);pointer-events:none}
.header .subtitle{color:#8f9ba7;font-weight:400;margin-top:10px;letter-spacing:.02em;font-family:'JetBrains Mono',monospace;font-size:.85rem}
.banner{background:rgba(255,255,255,.55);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border-bottom:1px solid var(--line);padding:12px 0;font-size:.85rem;color:var(--ink2);font-family:'JetBrains Mono',monospace;position:sticky;top:0;z-index:5}
.banner.warn{background:rgba(245,179,1,.35)}
.legend span{margin-right:14px;display:inline-flex;align-items:center;gap:6px} .legend .dot{width:9px;height:9px;animation:none}
.section{padding:44px 0} .section-sand{background:transparent}
.card{background:var(--glass);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border:1px solid rgba(255,255,255,.7);box-shadow:0 1px 0 rgba(255,255,255,.8) inset,0 12px 40px -20px rgba(15,20,26,.35);border-radius:18px;padding:26px;margin-bottom:14px;transition:transform .25s ease,box-shadow .25s ease}
.card.prop:hover{transform:translateY(-2px);box-shadow:0 1px 0 rgba(255,255,255,.9) inset,0 22px 50px -22px rgba(15,20,26,.45)}
.tag{display:inline-block;padding:.28rem .8rem;border-radius:100rem;font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;margin-left:4px;vertical-align:middle;font-family:'JetBrains Mono',monospace}
.tag-dark{background:var(--graphite);color:var(--silver)} .tag-sand{background:rgba(15,20,26,.06);color:var(--ink2);border:1px solid var(--line)}
.tag-red{background:var(--red);color:#fff} .tag-amber{background:var(--amber);color:#1a1a1a}
.tag-esc{background:var(--red);color:#fff;animation:escalate 1.6s ease-in-out infinite}
.muted{color:var(--mute)} .small{font-size:.85rem} .warn-text{color:var(--red)}
.light{display:inline-flex;align-items:center;gap:7px;margin-right:16px;font-size:.78rem;color:var(--ink2)} .lbl{color:var(--mute)}
.dot{width:11px;height:11px;border-radius:50%;display:inline-block;flex:none;position:relative;box-shadow:0 0 0 0 currentColor}
.dot[style*="#c0392b"]{background:var(--red)!important;animation:pulse-red 1.4s ease-out infinite}
.dot[style*="#d9a53a"]{background:var(--amber)!important;animation:pulse-soft 2.6s ease-out infinite}
.dot[style*="#3f8f5a"]{background:var(--green)!important;animation:pulse-soft 3.4s ease-out infinite}
.dot[style*="#b5b0a6"]{background:var(--grey)!important;opacity:.7}
.dir{position:absolute;left:0;top:.55em;width:8px;height:8px;border-radius:50%;background:var(--grey)} .dir-positive{background:var(--green)} .dir-negative{background:var(--red)}
.lights-row{margin:10px 0} .lights-row.inline{margin:0 0 0 12px;display:inline}
.prop-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}
.route{font-size:1.2rem;font-weight:600;margin:14px 0 4px;color:var(--ink)}
.paths{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:18px}
.path{background:var(--glass2);border:1px solid rgba(255,255,255,.9);border-radius:14px;padding:16px} .path-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px} .path ul{margin-top:8px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:32px} @media(max-width:900px){.cols,.paths{grid-template-columns:1fr}}
table{width:100%;border-collapse:collapse;font-size:.85rem} th{text-align:left;font-weight:600;padding:10px 8px;border-bottom:1px solid rgba(15,20,26,.25);white-space:nowrap;font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;color:var(--mute)} td{padding:9px 8px;border-bottom:1px solid var(--line);vertical-align:middle} tr:hover td{background:rgba(255,255,255,.55)}
.table-wrap{overflow-x:auto} ul{padding-left:18px} li{margin:5px 0} .facts li{list-style:none;position:relative;padding-left:14px}
summary{cursor:pointer;list-style:none} summary::-webkit-details-marker{display:none} summary::before{content:"▸";display:inline-block;margin-right:8px;color:var(--mute);transition:transform .2s} details[open] summary::before{transform:rotate(90deg)}
a{color:inherit;text-decoration-color:rgba(15,20,26,.3);text-underline-offset:2px} a:hover{text-decoration-color:var(--accent)}
.footer{background:var(--graphite);color:#8f9ba7;padding:28px;text-align:center;font-size:.78rem;font-family:'JetBrains Mono',monospace}
@keyframes pulse-red{0%{box-shadow:0 0 0 0 rgba(239,68,68,.55)}70%{box-shadow:0 0 0 9px rgba(239,68,68,0)}100%{box-shadow:0 0 0 0 rgba(239,68,68,0)}}
@keyframes pulse-soft{0%{box-shadow:0 0 0 0 rgba(15,20,26,.22)}70%{box-shadow:0 0 0 7px rgba(15,20,26,0)}100%{box-shadow:0 0 0 0 rgba(15,20,26,0)}}
@keyframes escalate{0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,.6)}50%{box-shadow:0 0 0 8px rgba(239,68,68,0)}}
@media (prefers-reduced-motion: reduce){.dot,.tag-esc,.card{animation:none!important;transition:none!important}}
"""
LIGHT_HEX = {"green": "#3f8f5a", "yellow": "#d9a53a", "red": "#c0392b", "grey": "#b5b0a6"}
DIM_LABELS = [("funding_market", "Funding"), ("capital_access", "Capital access"), ("regulation", "Regulation"),
              ("strategics", "Strategics"), ("exit_comps", "Exit comps"), ("consolidators", "Consolidators")]
HEALTH_LABELS = [("runway", "Runway"), ("risk_band", "Risk band"), ("kpi_trend", "KPI trend"), ("contact", "Contact"), ("momentum", "Momentum")]
PATH_LABELS = [("growth_round", "Follow-on / growth round"), ("strategic_ma", "Strategic M&A"), ("roll_up", "Roll-up / consolidation")]
URGENCY_CLS = {"ESCALATE": "tag-esc", "NOW": "tag-red", "QUARTER": "tag-amber", "WATCH": "tag-sand"}


def esc(s, limit: int = MAX_TEXT) -> str:
    s = "" if s is None else str(s)
    if len(s) > limit:
        s = s[: limit - 1] + "…"
    return html.escape(s, quote=True)


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "x"


def dot(light: dict, label: str | None = None) -> str:
    c = light.get("colour", "grey")
    title = esc(light.get("reason", ""), 200)
    lab = f'<span class="lbl">{esc(label)}</span>' if label else ""
    return f'<span class="light" title="{title}"><span class="dot" style="background:{LIGHT_HEX[c]}"></span>{lab}</span>'


def link(url, text) -> str:
    if url and str(url).startswith(("http://", "https://")):
        return f'<a href="{esc(url, 500)}" target="_blank" rel="noopener">{esc(text)}</a>'
    return esc(text)


def fact_li(f: dict) -> str:
    src = link(f.get("source_url"), "source") if f.get("source_url") else '<span class="muted">internal</span>'
    return (f'<li><span class="dir dir-{esc(f.get("direction"))}"></span>'
            f'{esc(f.get("claim"))} <span class="muted small">{esc(f.get("date") or "undated")} · {src} · {esc(f.get("confidence"))}</span></li>')


def party_li(p: dict, limit: int = 180) -> str:
    intent = ' <span class="tag tag-sand">looking</span>' if p.get("intent") == "stated_looking_for" else ""
    return (f'<li>{link(p.get("source_url"), p["name"])}{intent} <span class="muted small">({esc(p.get("kind"))}, '
            f'{esc(p.get("date") or "undated")}) {esc(p.get("evidence"), limit)}</span></li>')


def tag(text: str, cls: str = "tag-dark") -> str:
    return f'<span class="tag {cls}">{esc(text, 40)}</span>'


def _paths_block(c: dict) -> str:
    cols = []
    for key, label in PATH_LABELS:
        p = c["paths"][key]
        rec = ' <span class="tag tag-dark">recommended</span>' if c["recommended_path"] == key else ""
        parties = "".join(party_li(x) for x in c["counterparties"].get(key, [])) or '<li class="muted">no dated counterparties found</li>'
        cols.append(f'<div class="path"><div class="path-head">{dot(p)}<strong>{esc(label)}</strong>{rec}</div>'
                    f'<div class="small muted">{esc(p.get("reason"), 200)}</div><ul class="small">{parties}</ul></div>')
    return f'<div class="paths">{"".join(cols)}</div>'


def _matches_block(c: dict) -> str:
    if not c.get("matches"):
        return ""
    items = "".join(
        f'<li>{link(m.get("source_url"), m["name"])} <span class="muted small">({esc(m["kind"])}, {esc(m.get("date") or "undated")}) '
        f'{esc(m.get("evidence"), 200)} · matches: {esc(", ".join(m.get("match_terms") or []), 120)}</span></li>' for m in c["matches"])
    return f'<h4>Lid to pot: parties that said they look for this</h4><ul class="small">{items}</ul>'


def render_html(pulse: dict, run_report: dict, segments_cfg: dict, demo: bool = False) -> str:
    as_of = pulse["as_of"]
    companies = pulse["companies"]
    n_ok = sum(1 for w in run_report["workers"] if w["ok"])
    n_all = len(run_report["workers"])
    total_cost = sum(w.get("cost_usd") or 0 for w in run_report["workers"])
    banner_cls = "" if n_ok == n_all else " warn"
    if demo:
        subtitle = f"Illustrative demo · fictional companies and numbers · as of {esc(as_of)} · {len(companies)} companies"
        banner_text = ("DEMO DATA. Every company, cash figure and internal note on this page is invented. Funds and corporates are real, "
                       "the deals and quotes attributed to them here are illustrative. The scoring rules are the real ones.")
    else:
        subtitle = f"Oyster Bay Venture Capital · as of {esc(as_of)} · {len(companies)} companies · confidential"
        banner_text = f"Run {esc(run_report['run_id'])} · {n_ok}/{n_all} workers succeeded · research cost {total_cost:.2f} USD · generated {esc(run_report['generated_at'])}"

    prop_cards = []
    for c in companies:
        internal = c.get("internal") or {}
        prop_cards.append(f"""
        <div class="card prop" id="p-{esc(slug(c['company']))}">
          <div class="prop-head">
            <div><h3>{esc(c['company'])}</h3><div class="muted small">{esc(segments_cfg.get(c['segment'], {}).get('label', c['segment']))} · {esc(', '.join(c['funds']))} · cash {esc(internal.get('cash') or 'n/a')} ({esc(internal.get('cash_as_of') or 'n/a')}) · runway {esc(f"{internal['runway_months']:.1f}" if internal.get('runway_months') is not None else 'n/a')} m</div></div>
            <div>{tag(c['urgency'], URGENCY_CLS[c['urgency']])} {tag('company ' + c['health'].lower())} {tag('market ' + c['market'].lower())}</div>
          </div>
          <p class="route">{esc(c['recommended_label'])}</p>
          <p class="small muted">Trigger: {esc(c['urgency_reason'])}</p>
          <div class="lights-row">{''.join(dot(c['health_lights'][k], l) for k, l in HEALTH_LABELS)}</div>
          <div class="lights-row">{''.join(dot(c['market_lights'][k], l) for k, l in DIM_LABELS)}</div>
          {_paths_block(c)}
          {_matches_block(c)}
          <p class="small"><a href="#c-{esc(slug(c['company']))}">facts and internal notes</a></p>
        </div>""")

    grid_rows = []
    for c in companies:
        cells = "".join(f"<td>{dot(c['health_lights'][k])}</td>" for k, _ in HEALTH_LABELS)
        cells += "".join(f"<td>{dot(c['market_lights'][k])}</td>" for k, _ in DIM_LABELS)
        cells += "".join(f"<td>{dot(c['paths'][k])}</td>" for k, _ in PATH_LABELS)
        grid_rows.append(f"<tr><td><a href='#p-{esc(slug(c['company']))}'>{esc(c['company'])}</a></td>{cells}"
                         f"<td>{esc(c['recommended_path'])}</td><td>{esc(c['urgency'])}</td></tr>")
    grid_head = ("".join(f"<th>{l}</th>" for _, l in HEALTH_LABELS) + "".join(f"<th>{l}</th>" for _, l in DIM_LABELS)
                 + "".join(f"<th>{l}</th>" for _, l in PATH_LABELS))

    details = []
    for c in companies:
        internal = c.get("internal") or {}
        notes = "".join(f"<li>{esc(n)}</li>" for n in internal.get("notes", [])) or "<li class='muted'>no internal notes returned</li>"
        att = "".join(f"<li>{esc(a, 600)}</li>" for a in c["attention_items"]) or "<li class='muted'>none</li>"
        ext = "".join(fact_li(f) for f in c["external_facts"]) or "<li class='muted'>no external facts found</li>"
        cov = "".join(f"<li>{esc(x)}</li>" for x in c["coverage"]) or "<li class='muted'>complete</li>"
        seg_check = c.get("segment_check")
        seg_note = "" if not seg_check or seg_check.strip().lower().startswith("fits") else f"<p class='small warn-text'>Segment check: {esc(seg_check)}</p>"
        details.append(f"""
        <details class="card" id="c-{esc(slug(c['company']))}">
          <summary><strong>{esc(c['company'])}</strong> · {esc(c['recommended_path'])} · {esc(c['urgency'])}
            <span class="muted small">process {esc(internal.get('active_process') or 'unknown')} · deadline {esc(internal.get('process_deadline') or 'none')}</span>
          </summary>
          {seg_note}
          <div class="cols">
            <div><h4>Internal (Jarvis)</h4><ul class="small">{notes}</ul><h4>Attention items (risk rank)</h4><ul class="small">{att}</ul></div>
            <div><h4>Own news (last 12 months)</h4><ul class="small facts">{ext}</ul><h4>Coverage</h4><ul class="small">{cov}</ul></div>
          </div>
        </details>""")

    seg_blocks = []
    seg_data = run_report.get("segment_data", {})
    for sid, sc in pulse["segments"].items():
        cfg = segments_cfg.get(sid, {})
        data = seg_data.get(sid)
        lights = "".join(dot(sc["lights"][k], l) for k, l in DIM_LABELS)
        if data is None:
            body = "<p class='muted small'>segment research unavailable this run</p>"
        else:
            funds = "".join(party_li({**f, "kind": "fund"}) for f in data["capital_access"]["active_funds"]) or "<li class='muted'>none found</li>"
            players = "".join(party_li({**p, "kind": "strategic"}) for p in data["strategics"]["players"]) or "<li class='muted'>none found</li>"
            cons = "".join(party_li({**p, "kind": "consolidator"}) for p in data.get("consolidators", {}).get("players", [])) or "<li class='muted'>none found</li>"
            deals = "".join(f"<li>{esc(d['kind'])}: {esc(d['target'])} ← {link(d.get('source_url'), d['acquirer_or_lead'])} <span class='muted small'>{esc(d.get('date') or 'undated')} {esc(d.get('value') or '')}</span></li>" for d in data["exit_comps"]["deals"]) or "<li class='muted'>none found</li>"
            facts = "".join(fact_li(f) for dim in ("funding_market", "regulation", "consolidators") for f in data.get(dim, {}).get("facts", []))
            body = f"""<div class="cols">
              <div><h4>Active funds (12 m)</h4><ul class="small">{funds}</ul><h4>Vocal strategics (12 m)</h4><ul class="small">{players}</ul></div>
              <div><h4>Consolidators (24 m)</h4><ul class="small">{cons}</ul><h4>Exit comps (24 m)</h4><ul class="small">{deals}</ul></div>
            </div><h4>Funding, regulation and consolidation facts</h4><ul class="small facts">{facts or "<li class='muted'>none</li>"}</ul>"""
        seg_blocks.append(f"""<details class="card"><summary><strong>{esc(cfg.get('label', sid))}</strong> · market {esc(sc['market'])} <span class="lights-row inline">{lights}</span></summary>{body}</details>""")

    macro = pulse.get("macro")
    if macro:
        macro_html = f"""<p>{esc(macro['summary'], 800)}</p>
        <p class="small">Rates: <strong>{esc(macro['interest_rate_direction'])}</strong> · Venture funding: <strong>{esc(macro['venture_funding_direction'])}</strong> · Agrifood funding: <strong>{esc(macro['agrifood_funding_direction'])}</strong></p>
        <details><summary class="small">facts ({len(macro['facts'])})</summary><ul class="small facts">{''.join(fact_li(f) for f in macro['facts'])}</ul></details>"""
    else:
        macro_html = "<p class='muted'>macro research unavailable this run</p>"

    workers_rows = "".join(
        f"<tr><td>{esc(w['name'])}</td><td>{'ok' if w['ok'] else esc(w.get('error_kind'))}</td><td>{w['turns']}</td>"
        f"<td>{w['duration_s']:.0f}s</td><td>{(w.get('cost_usd') or 0):.2f}</td><td class='small muted'>{esc(w.get('error') or '', 160)}</td></tr>"
        for w in sorted(run_report["workers"], key=lambda w: (w["ok"], w["name"])))

    legend = "".join(f'<span><span class="dot" style="background:{LIGHT_HEX[k]}"></span> {v}</span>'
                     for k, v in (("green", "supportive"), ("yellow", "mixed"), ("red", "adverse"), ("grey", "no data")))

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portfolio Market Pulse {esc(as_of)} — Oyster Bay VC</title>
<style>{CSS}</style></head><body>
<div class="header"><div class="container"><h1>Portfolio Market Pulse</h1><div class="subtitle">{subtitle}</div></div></div>
<div class="banner{banner_cls}"><div class="container">{banner_text} · <span class="legend">{legend}</span></div></div>

<div class="section"><div class="container"><h2>Macro</h2><div class="card">{macro_html}</div></div></div>

<div class="section section-sand"><div class="container"><h2>Proposals, by urgency</h2>{''.join(prop_cards)}</div></div>

<div class="section"><div class="container"><h2>Portfolio grid</h2><div class="card table-wrap"><table><thead><tr><th>Company</th>{grid_head}<th>Path</th><th>Urgency</th></tr></thead><tbody>{''.join(grid_rows)}</tbody></table></div>
<p class="small muted">Five internal lights (Jarvis), six segment market lights (research), three path lights (rules). Hover a light for the rule that produced it.</p></div></div>

<div class="section section-sand"><div class="container"><h2>Companies: facts and notes</h2>{''.join(details)}</div></div>

<div class="section"><div class="container"><h2>Segments</h2>{''.join(seg_blocks)}</div></div>

<div class="section section-sand"><div class="container"><h2>Run report</h2><div class="card table-wrap"><table><thead><tr><th>Worker</th><th>Status</th><th>Turns</th><th>Time</th><th>USD</th><th>Error</th></tr></thead><tbody>{workers_rows}</tbody></table></div></div></div>

<div class="footer">{"Portfolio Market Pulse · illustrative demo · all company data fictional" if demo else "OYSTERBAY · Portfolio Market Pulse · confidential · internal marks and cash positions, do not distribute"}</div>
</body></html>"""


def render_markdown(pulse: dict, run_report: dict, segments_cfg: dict, demo: bool = False) -> str:
    lines = [f"# Portfolio Market Pulse, as of {pulse['as_of']}", ""]
    if demo:
        lines += ["_Illustrative demo. Every company and number is fictional._", ""]
    m = pulse.get("macro")
    if m:
        lines += [f"**Macro.** {m['summary']}", "",
                  f"Rates: {m['interest_rate_direction']} · Venture funding: {m['venture_funding_direction']} · Agrifood: {m['agrifood_funding_direction']}", ""]
    lines += ["## Proposals", ""]
    for c in pulse["companies"]:
        lab = segments_cfg.get(c["segment"], {}).get("label", c["segment"])
        paths = " / ".join(f"{l}: {c['paths'][k]['colour']}" for k, l in PATH_LABELS)
        lines.append(f"- **{c['company']}** ({lab}) · {c['urgency']} · company {c['health']} / market {c['market']} · **{c['recommended_label']}**. Trigger: {c['urgency_reason']}. Paths: {paths}.")
        cp = c["counterparties"].get(c["recommended_path"], [])
        if cp:
            lines.append("  - Counterparties: " + "; ".join(f"{p['name']} ({p['kind']}, {p.get('date') or 'undated'})" for p in cp[:4]))
        if c.get("matches"):
            lines.append("  - Lid to pot: " + "; ".join(f"{x['name']} ({', '.join(x['match_terms'][:3])})" for x in c["matches"][:3]))
    n_ok = sum(1 for w in run_report["workers"] if w["ok"])
    lines += ["", f"_{n_ok}/{len(run_report['workers'])} workers succeeded. Generated {run_report['generated_at']}._"]
    return "\n".join(lines) + "\n"


def artifact_body(full_html: str, title: str = "Portfolio Market Pulse") -> str:
    """Body-only variant for hosts that supply their own document skeleton: <title> + <style> + body content."""
    style = re.search(r"<style>(.*?)</style>", full_html, re.S)
    body = re.search(r"<body>(.*?)</body>", full_html, re.S)
    return (f"<title>{esc(title, 80)}</title>\n"
            f"<style>{style.group(1) if style else ''}</style>\n{body.group(1) if body else full_html}")


def now_iso() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
