# Portfolio Market Pulse

Autonomous weekly read on every active Oyster Bay portfolio company: internal health from Jarvis crossed with the external market of its segment, scored by fixed rules into traffic lights, a route recommendation and an urgency flag. Output is one HTML dashboard with every fact cited.

## What it does

```
run.py (deterministic orchestrator)
  1. inventory worker ── Jarvis: crm_list_portfolio + portfolio_risk_rank ──▶ internal health per company
  2. config/segments.yaml ── curated map company → segment (peers, strategics, regulation topics)
  3. research fan-out, parallel headless `claude -p` workers, each bound to a JSON schema:
       macro (1)            rates, venture and agrifood funding climate, exit window
       segment (per segment) funding rounds · active growth funds · regulation · vocal strategics · exit comps
       company (per company) Jarvis current state + KPIs, external news
  4. pulse/scoring.py ── pure functions: dimension lights (green/yellow/red/grey), company health,
       market strength, route (2x2 matrix), urgency (NOW / QUARTER / WATCH), counterparties
  5. pulse/render.py ── out/index.html (OB CI), out/pulse.md, out/pulse.json, out/run_report.json
```

Three paths per company, each with its own light and counterparties, recommended path = the greenest (ties broken by company health: STRONG prefers a round, WEAK prefers M&A then roll-up):

| Path | Green when | Counterparties |
|---|---|---|
| Follow-on / growth round | capital access and funding market green, company STRONG | funds active in the segment, newly closed funds with a fitting mandate |
| Strategic M&A | vocal strategics and exit comps green | corporates that said what they look for, recent acquirers |
| Roll-up / consolidation | consolidators light green | PE platforms, buy-and-build holdings, funded peers |

All three red: "bridge and prepare a structured process". Overrides: `exit_in_progress` (curated) and `wind_down` (from Jarvis).

Company health is a weighted mean of five lights (runway 2.0, risk band 1.5, KPI trend 1.5, contact 0.5, own-news momentum 1.0). Urgency: **ESCALATE** when runway is under 8 weeks (find a solution immediately), **NOW** for runway under 6 months, a documented deadline within 60 days, an active M&A, bridge or wind-down process, or weak company in weak market; **QUARTER** for runway under 12 months, a weak side, or an open fundraise; else **WATCH**.

"Lid to pot": every fund or corporate the research found with a stated mandate ("we look for X") is matched by keyword overlap against the segment and the company's one-liner and shown on the card when it fits.

Grey means "fewer than two dated facts", never a default colour. Every light shows the rule that produced it on hover. Scoring never reads free text from the web, only schema fields; the LLM workers classify each fact's direction with a source, the aggregation is code.

The system never sends anything anywhere. It writes local files. `out/` and `data/runs/` contain confidential marks and cash positions and are gitignored.

## Inputs

- A machine where `claude` (Claude Code CLI) is logged in and has authorised the Jarvis MCP server once (`claude` → `/mcp` → jarvis). Workers reuse both sessions. Alternatively set `ANTHROPIC_API_KEY` in `.env` (see `.env.example`; key in GCP Secret Manager `ob-sourcing-brain`).
- `config/segments.yaml`: the curated segment map. A company that appears in Jarvis but not here is skipped with a warning. Add it.
- `config/mcp.json`: Jarvis gateway URL.

## How to run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
```

Useful flags: `--companies Meatly,Dropz` (subset), `--reuse` (keep today's finished workers, rerun the rest), `--replay 2026-09-08` (re-score a saved run without any worker), `--dry-run` (print the plan), `--max-workers 8`, `--model claude-sonnet-5`.

Exit codes: 0 clean, 1 partial (some workers failed, dashboard still rendered with a warning banner), 2 fatal (inventory or authentication failed; the message names the fix).

Tests, all offline:

```bash
.venv/bin/pytest -q
```

Weekly schedule on this Mac (launchd): see `schedule/README.md`.

## Known limits

- Traffic-light colours (green/amber/red) are outside the OB palette. They are used only for the 12px status dots because the brief asks for a traffic light.
- Fact direction is judged by the research worker per fact. Everything above the fact level is deterministic.
- One run costs roughly 5 to 10 USD on Sonnet and takes about 10 minutes with 8 parallel workers.
- See `TODOS.md` for what was deliberately left out.
