"""Prompt builders for the four worker types.

Prompts are plain text. They tell the worker which tools to use in which order,
what counts as a fact, and that the only acceptable output is the schema.
"""
from __future__ import annotations

NO_SHELL = """
YOU HAVE NO SHELL. Only the tools named in this prompt exist for you. Do not call Bash, Write, Read, Edit or any file tool; those calls are denied and waste your turns. Never write helper scripts or files. Merge, count and format everything in your own reasoning and answer directly with the structured output as your final message.
"""

COMMON_RULES = NO_SHELL + """
RULES FOR EVERY FACT
- A fact is one dated, sourced claim. Prefer facts from the last 12 months. Anything older than 24 months is out unless it is the most recent thing that exists.
- date: YYYY-MM-DD or YYYY-MM if you know it, else null. Never guess a date.
- source_url: the page you actually read. For Jarvis facts use null and source_type "jarvis".
- direction: positive means better funding, access, regulatory tailwind or buyer appetite for companies in this segment; negative the opposite; neutral if it is context only.
- confidence: high = primary source or two independent sources; medium = one reputable secondary source; low = single weak source or partial read.
- Never invent a fund, buyer, deal or round. If you cannot find something, return an empty list. Empty is a valid and expected answer.
- Write claims in English, one sentence, max 400 characters, with the number and the counterparty when known.
- Return only the structured output that matches the schema. No prose outside it.
"""


def inventory_prompt(as_of: str) -> str:
    return f"""Today is {as_of}. You are building the internal health inventory of Oyster Bay's portfolio.

STEPS
1. Call mcp__jarvis__crm_list_portfolio once. Take every company with its name, orgId, status and funds.
2. Call mcp__jarvis__portfolio_risk_rank once with limit 20. For each ranked company copy risk_score, band, daysSinceContact, the "reasons" list verbatim (each item max 600 chars, trim if longer) and the coverage list.
3. Merge by company name in your head. Companies present in the portfolio list but absent from the ranking get risk_band null, risk_score null, days_since_contact null, empty attention_items, and a coverage note "not ranked (status or skipped)".
4. Set as_of to the as_of value returned by the tools.

Exactly two tool calls, then answer. Do not add commentary. Return only the schema.
{NO_SHELL}"""


def macro_prompt(as_of: str) -> str:
    return f"""Today is {as_of}. You are researching the macro environment for a European early-stage agri-food venture portfolio.

Use WebSearch (and WebFetch to read a result when the snippet is not enough). Aim for 8 to 14 facts total across these questions:
- Interest rates: latest ECB and Fed decisions and stated direction (last 3 months).
- Venture funding environment overall: latest quarterly data on European and global VC funding, deal counts, growth-stage activity (last 2 quarters).
- Agrifood-tech funding specifically: latest AgFunder, PitchBook, Dealroom or similar data on agrifood / foodtech / agtech funding and deal counts (last 12 months).
- Exit environment: IPO window, M&A volumes for consumer and agri-food (last 2 quarters).

Set the three direction fields from the facts you found, "unknown" if you found nothing.
summary: 3 to 5 sentences, sober, no adjectives, numbers with dates.
{COMMON_RULES}"""


def segment_prompt(as_of: str, segment_id: str, seg: dict, portfolio_companies: list[str]) -> str:
    peers = ", ".join(seg.get("peers") or []) or "none listed"
    strategics = ", ".join(seg.get("known_strategics") or []) or "none listed"
    reg = "; ".join(seg.get("regulation_watch") or []) or "none listed"
    keywords = ", ".join(seg.get("keywords") or [])
    ours = ", ".join(portfolio_companies) or "none"
    return f"""Today is {as_of}. You are researching the market segment "{seg['label']}" (segment_id: {segment_id}) for a venture investor.
Oyster Bay portfolio companies in this segment: {ours}. Do not research those companies themselves here; another worker does that. Research the segment around them.

Search hints: {keywords}
Known peers to check for rounds, exits, shutdowns: {peers}
Corporates to check for statements, partnerships, acquisitions: {strategics}
Regulatory topics to check: {reg}

TOOLS, IN THIS ORDER
1. mcp__jarvis__knowledge_search with 2 to 3 queries about this segment (funding, M&A, regulation). Jarvis holds industry reports and internal notes. Facts from it are source_type "jarvis", source_url null.
2. WebSearch, several targeted queries per dimension below. Use WebFetch to read a page when you need the number or the date.

DIMENSIONS TO FILL
- funding_market: rounds announced in this segment in the last 12 months (who, how much, when, lead), plus any data on total segment funding vs prior year. 4 to 8 facts.
- capital_access: (a) growth-stage or specialist funds that led or joined a round in this segment in the last 12 months (intent "acted", the deal as evidence); (b) funds that closed a NEW fund in the last 12 months and stated a mandate that covers this segment: fund name, size, close date, and their own words on what they look for (intent "stated_looking_for", mandate_keywords from their words). 3 to 8 entries if they exist. Search e.g. "<segment> fund closes", "new fund agrifood growth 2026", "<segment> investor mandate".
- regulation: approvals, bans, labelling rules, subsidies, tariffs, policy signals affecting this segment in the last 18 months. 2 to 6 facts.
- strategics: corporates that in the last 12 months (a) publicly said what they look for: acquisition targets, partnership calls, venture programs, "we are looking for X" statements at conferences or in earnings calls (intent "stated_looking_for", mandate_keywords from their words); or (b) partnered with, invested in, or acquired a company in this segment (intent "acted"). List each in players with the quote or action as evidence. 3 to 8 entries if they exist.
- exit_comps: acquisitions, mergers, large growth rounds, and shutdowns of companies in this segment in the last 24 months. List each in deals. 3 to 8 entries if they exist.
- consolidators: PE platforms, buy-and-build holdings, roll-up vehicles and well-funded peers that bought or merged two or more companies in this segment in the last 24 months, or announced a consolidation strategy for it (intent stated_looking_for or acted). Search e.g. "<segment> roll-up", "<segment> buy and build", "<segment> consolidation platform", "<segment> PE platform acquisition". 0 to 6 entries; empty is a valid answer.

The "stated_looking_for" entries matter most: they are the lid that may fit a pot in our portfolio. Quote their words in evidence and keep mandate_keywords faithful to those words.

Set segment_id to "{segment_id}".
{COMMON_RULES}"""


def company_prompt(as_of: str, name: str, org_id: str | None, one_liner: str, segment_label: str,
                   attention_items: list[str]) -> str:
    items = "\n".join(f"- {a[:400]}" for a in attention_items[:6]) or "- none recorded"
    org = org_id or "unknown; resolve by company name"
    return f"""Today is {as_of}. You are assembling the current picture for the Oyster Bay portfolio company "{name}" (Affinity org_id {org}).
What we believe it does: {one_liner}. Curated segment: {segment_label}.

Internal attention items already known (from the risk ranking, do not repeat them as facts, use them to know what to verify):
{items}

TOOLS, IN THIS ORDER
1. mcp__jarvis__company_current_state for "{name}" (pass org_id if known). Read runway, cash, KPI trend, open processes (fundraise, M&A mandate, bridge, wind-down) and any documented decision or cash-out date.
2. mcp__jarvis__fund_kpis with the org_id, limit 30. Use it to confirm cash and the direction of revenue or ARR over the last periods.
3. mcp__jarvis__knowledge_search scoped to the company, one or two queries: "fundraise status", "runway cash", "acquisition interest".
4. WebSearch for the company name plus "funding", "acquisition", "partnership", "launch", "layoffs" in the last 12 months. 2 to 6 external facts. Press about the company itself only.

FILL internal
- runway_months: months of cash left as stated or as latest cash divided by latest monthly burn. null if not derivable. runway_as_of: the date of the data used.
- cash and cash_as_of: latest cash reading with currency.
- kpi_trend: revenue/ARR direction over the last 2 to 3 reported periods; "unknown" if fewer than 2 periods.
- active_process: fundraise, m_and_a, bridge, wind_down, none, or unknown. Only from Jarvis evidence.
- process_deadline: a documented decision date, cash-out date or closing date, else null.
- data_status: ok if runway and kpi_trend are grounded; partial if one is; jarvis_error if a Jarvis call failed; no_data if nothing came back.
- notes: up to 6 short lines with the numbers and their as-of dates, sourced from Jarvis.

segment_check: "fits" or a better segment_id from this list: cultivated_meat, plant_based_meat, organic_food_cpg_dach, functional_beverage_d2c, food_robotics, precision_ag_sensing, seed_and_crop_genetics, ag_biologicals, biomaterials, precision_fermentation, alt_cocoa_ingredients, food_ingredients_b2b. One line.

Set company to "{name}".
{COMMON_RULES}"""
