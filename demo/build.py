"""Illustrative demo data for showcasing the Portfolio Market Pulse without confidential information.

Companies, cash positions, runway figures and internal notes are fictional.
Market evidence is real and linked: nine segments are loaded from demo/segments/*.json, a snapshot
of the web-sourced facts from a live research run (Jarvis-sourced facts removed); three segments
are hand-written from public articles with their URLs. The scoring engine and rules are the real ones.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

AS_OF = date(2026, 9, 8)
HERE = Path(__file__).resolve().parent


def _d(days_ago: int) -> str:
    return (AS_OF - timedelta(days=days_ago)).isoformat()


def fact(claim, d, direction="positive", conf="high", url=None):
    return {"claim": claim, "date": d, "direction": direction, "source_url": url, "source_type": "web" if url else "jarvis", "confidence": conf}


def party(name, evidence, d, url, intent="acted", kw=()):
    return {"name": name, "evidence": evidence, "date": d, "source_url": url, "intent": intent, "mandate_keywords": list(kw)}


def deal(target, acquirer, kind, d, url, value=None):
    return {"target": target, "acquirer_or_lead": acquirer, "kind": kind, "date": d, "value": value, "source_url": url}


def segment(sid, funding, funds, reg, players, deals, cons):
    return {"segment_id": sid, "funding_market": {"facts": funding}, "capital_access": {"facts": [], "active_funds": funds},
            "regulation": {"facts": reg}, "strategics": {"facts": [], "players": players},
            "exit_comps": {"facts": [], "deals": deals}, "consolidators": {"facts": [], "players": cons}}


def internal(runway, cash, trend, process="none", deadline=None, notes=(), days_ago=20):
    return {"runway_months": runway, "runway_as_of": _d(days_ago), "cash": cash, "cash_as_of": _d(days_ago), "kpi_trend": trend,
            "active_process": process, "process_deadline": deadline, "data_status": "ok", "notes": list(notes)}


def company(name, int_, ext):
    return {"company": name, "internal": int_, "external_facts": ext, "segment_check": "fits"}


def inv(name, band, days, funds=("Fund II",), items=()):
    return {"name": name, "org_id": None, "status": "active", "funds": list(funds), "risk_band": band, "risk_score": {"low": 2, "medium": 5, "high": 8}[band],
            "days_since_contact": days, "attention_items": list(items), "coverage_notes": []}


# ---- real, linked public sources used in the hand-written segments ----
ACCEL_MIND = "https://www.accel.com/news/mind-robotics-bringing-ai-to-the-physical-world"
ACCEL_FUND = "https://techcrunch.com/2026/04/15/accel-raises-5b-to-back-late-stage-bets/"
CRUNCH_ROBOTICS = "https://news.crunchbase.com/robotics/startup-venture-funding-surges-2026-data/"
PHYS_AI = "https://valueaddvc.com/pulse/physical-ai-funding-47-billion-h1-2026-data"
FOURAG = "https://betakit.com/4ag-robotics-looks-to-grow-fleet-of-mushroom-harvesting-robots-with-40-million-series-b-round/"
AGRIPASS = "https://www.agtechnavigator.com/Article/2026/03/05/weed-management-how-this-startup-is-helping-farmers-improve-yields/"
OEM_AUTONOMY = "https://www.precisionfarmingdealer.com/articles/5150-acquisitions-investments-accelerate-oems-autonomous-capabilities"
OEM_OUTLOOK = "https://www.farm-equipment.com/articles/24910-cnh-agco-and-kubota-share-outlook-on-autonomy"
DEERE_BEARFLAG = "https://techcrunch.com/2021/08/05/john-deere-buys-autonomous-tractor-startup-bear-flag-robotics/"
LK_GREENFORCE = "https://vegconomist.com/investments-finance/investments-acquisitions/livekindly-collective-acquires-german-plant-based-brand-greenforce/"
LK_TINDLE = "https://www.greenqueen.com.hk/livekindly-collective-tindle-foods-plant-based-meat-acquisition/"
LK_DALCO = "https://www.greenqueen.com.hk/livekindly-collective-dalco-hilton-food-group-plant-based-meat-acquisition/"
NOSH_CONSOL = "https://www.nosh.com/news/2026/plant-based-market-consolidation-continues-with-more-ma-from-livekindly"
GFI_PB = "https://gfi.org/resource/plant-based-meat-eggs-and-dairy-state-of-the-industry/"
SO_SERIES_B = "https://angelinvestorsnetwork.com/venture-capital/standing-ovations-342m-series-b-government-funds-beat-vcs"
PROVEG_PF = "https://proveg.org/policy/precision-fermentation/"
EU_BIOECON = "https://www.innovationnewsnetwork.com/building-europes-bioeconomy-with-precision-fermentation/64649/"
NOVONESIS_DSM = "https://www.novonesis.com/en/news/deal-acquire-dsm-firmenichs-share-feed-enzyme-alliance-completed-supporting-novonesis-growth"
SYNBIO_INVESTORS = "https://www.ellty.com/blog/synthetic-biology-investors"
SYNBIO_NEWS = "https://newmarketpitch.com/blogs/news/synthetic-biology-funding-news"

HANDWRITTEN = {
    "agri_robotics": segment(
        "agri_robotics",
        funding=[fact("Robotics startup venture funding surged to record levels in 2026, per Crunchbase data.", "2026-07", url=CRUNCH_ROBOTICS),
                 fact("Physical AI companies raised about $47bn in H1 2026.", "2026-07", url=PHYS_AI),
                 fact("4AG Robotics closed a $40m Series B to grow its fleet of mushroom-harvesting robots.", "2025-07", url=FOURAG, conf="medium")],
        funds=[party("Accel", "Co-led Mind Robotics' $500m Series A (a Rivian spinout) and describes its thesis as bringing AI to the physical world.", "2026-03", ACCEL_MIND, "acted"),
               party("Accel (Leaders Fund V)", "Raised $5bn for late-stage bets; the new fund names software, hardware, robotics and defense tech as focus areas.", "2026-04-15", ACCEL_FUND, "stated_looking_for", ["robotics", "hardware", "physical AI", "late-stage", "automation", "harvest"]),
               party("Harbor Venture Consulting", "Led AgriPass Robotics' $7.5m seed round for a computer-vision cultivation robot (March 2026).", "2026-03-05", AGRIPASS, "acted")],
        reg=[fact("Farm-equipment OEMs describe autonomy as a blended build-and-buy roadmap for 2026, with specialty crops first.", "2026-01", url=OEM_OUTLOOK, direction="positive", conf="medium"),
             fact("Kubota is working with a startup on autonomous specialty-crop projects starting in 2026.", "2026-01", url=OEM_OUTLOOK, conf="medium")],
        players=[party("Kubota", "Working with a startup on autonomous specialty-crop solutions in 2026; earlier acquired Bloomfield Robotics.", "2026-01", OEM_AUTONOMY, "stated_looking_for", ["autonomy", "specialty crops", "robotics", "agriculture"]),
                 party("John Deere", "Acquired Bear Flag Robotics for $250m and vision startup Light to build autonomous capability.", "2021-08-05", DEERE_BEARFLAG, "acted"),
                 party("CNH Industrial", "Acquired Raven Industries to close autonomy gaps; advanced cab-less robot concepts in 2025.", "2025-11", OEM_AUTONOMY, "acted")],
        deals=[deal("Bear Flag Robotics", "John Deere", "acquisition", "2021-08-05", DEERE_BEARFLAG, "$250m"),
               deal("Bloomfield Robotics", "Kubota", "acquisition", "2024-06", OEM_AUTONOMY),
               deal("Mind Robotics", "Accel (co-lead)", "growth_round", "2026-03", ACCEL_MIND, "$500m"),
               deal("4AG Robotics", "Series B syndicate", "growth_round", "2025-07", FOURAG, "$40m")],
        cons=[]),

    "plant_based_meat": segment(
        "plant_based_meat",
        funding=[fact("More than 80 plant-based companies have been acquired, merged, gone insolvent or shut down since September 2024.", "2026-07", url=NOSH_CONSOL, direction="negative"),
                 fact("GFI's State of the Industry report shows plant-based meat investment well below its 2021 peak.", "2026-04", url=GFI_PB, direction="negative", conf="medium")],
        funds=[],
        reg=[fact("Category fundamentals: retail sales stabilising in parts of Europe while investment stays thin.", "2026-04", url=GFI_PB, direction="neutral", conf="medium")],
        players=[party("Hilton Food Group", "Sold its Dutch meat-free business Dalco Food to LIVEKINDLY Collective for £5.4m, exiting the category.", "2026-05", LK_DALCO, "acted")],
        deals=[deal("Greenforce Future Food AG", "LIVEKINDLY Collective", "acquisition", "2026-07-01", LK_GREENFORCE),
               deal("TiNDLE Foods (foodservice business)", "LIVEKINDLY Collective", "acquisition", "2026-04", LK_TINDLE),
               deal("Dalco Food", "LIVEKINDLY Collective", "acquisition", "2026-05", LK_DALCO, "£5.4m")],
        cons=[party("LIVEKINDLY Collective", "Acquired Greenforce (signed 1 July 2026), TiNDLE's foodservice business and Dalco Food within months; positions itself as the consolidator of European plant-based brands.", "2026-07-01", LK_GREENFORCE, "stated_looking_for", ["plant-based", "brands", "Europe", "consolidation", "meat alternatives"]),
              party("LIVEKINDLY Collective (M&A strategy)", "Trade press describes an explicit step-up in M&A strategy.", "2026-07", NOSH_CONSOL, "stated_looking_for", ["plant-based", "M&A", "brands"])]),

    "precision_fermentation": segment(
        "precision_fermentation",
        funding=[fact("Standing Ovation closed a $34.2m Series B on 31 March 2026, led by Bpifrance's Ecotechnologies 2 fund and Crédit Mutuel Innovation.", "2026-03-31", url=SO_SERIES_B),
                 fact("June 2026 synthetic-biology rounds concentrated in precision fermentation, engineered enzymes, food ingredients and fermentation infrastructure.", "2026-06", url=SYNBIO_NEWS, conf="medium"),
                 fact("Government-backed patient capital is outpacing traditional VC in deep-tech biotech Series B rounds.", "2026-03-31", url=SO_SERIES_B, direction="neutral")],
        funds=[party("Bpifrance (Ecotechnologies 2)", "Led Standing Ovation's $34.2m Series B in precision fermentation.", "2026-03-31", SO_SERIES_B, "acted"),
               party("Crédit Mutuel Innovation", "Co-led the same Series B.", "2026-03-31", SO_SERIES_B, "acted"),
               party("Breakthrough Energy Ventures", "Listed among active investors in sustainable biomanufacturing and bio-based materials.", "2026-01", SYNBIO_INVESTORS, "stated_looking_for", ["biomanufacturing", "bio-based", "sustainable"]),
               party("EU Scale-up Europe Fund / EIC", "Instruments coordinated with the EIB aim to close late-stage gaps for biomanufacturing scale-up in Europe.", "2026-05", EU_BIOECON, "stated_looking_for", ["biomanufacturing", "scale-up", "Europe", "fermentation"])],
        reg=[fact("ProVeg policy brief: EU should streamline Novel Food approval for precision-fermentation products.", "2026-02", url=PROVEG_PF, direction="neutral", conf="medium"),
             fact("EU bioeconomy agenda supports precision fermentation and engineered biology scale-up.", "2026-05", url=EU_BIOECON)],
        players=[party("Novonesis", "Completed the €1.5bn acquisition of dsm-firmenich's share of the Feed Enzyme Alliance, supporting its biosolutions growth strategy.", "2026-02", NOVONESIS_DSM, "acted"),
                 party("dsm-firmenich", "Divested its feed-enzyme stake for €1.5bn, reshaping its portfolio.", "2026-02", NOVONESIS_DSM, "acted")],
        deals=[deal("Feed Enzyme Alliance (dsm-firmenich share)", "Novonesis", "acquisition", "2026-02", NOVONESIS_DSM, "€1.5bn"),
               deal("Standing Ovation", "Bpifrance / Crédit Mutuel Innovation", "growth_round", "2026-03-31", SO_SERIES_B, "$34.2m")],
        cons=[]),
}

EXTRA_SEGMENT_LABELS = {
    "precision_fermentation": {"label": "Precision fermentation and biomanufacturing platforms",
                               "keywords": ["precision fermentation", "biomanufacturing", "fermentation platform", "recurring revenue", "scale-up"]},
}


AUGMENT = {  # real, linked entries added to snapshot segments so the storyline reads end to end
    "food_robotics": [party("Accel (Leaders Fund V)", "Raised $5bn for late-stage bets naming robotics and hardware among its focus areas; also participated in Wonder's 2026 food-tech automation round.",
                            "2026-04-15", ACCEL_FUND, "stated_looking_for", ["robotics", "automation", "hardware", "late-stage", "kitchen"])],
}


def load_segments() -> dict:
    segs = dict(HANDWRITTEN)
    for p in sorted((HERE / "segments").glob("*.json")):
        d = json.loads(p.read_text())
        segs.setdefault(d["segment_id"], d)
    for sid, extra in AUGMENT.items():
        if sid in segs:
            segs[sid]["capital_access"]["active_funds"] = extra + segs[sid]["capital_access"]["active_funds"]
    # long syndicate names from the research snapshot read badly on a card: keep the lead, note the rest
    for seg in segs.values():
        for p in seg["capital_access"]["active_funds"]:
            if " / " in p["name"] and len(p["name"]) > 40:
                lead, _, rest = p["name"].partition(" / ")
                p["name"] = f"{lead} (with {rest.replace(' / ', ', ')})"
    return segs


# ---- fictional companies ----
COMPANIES_CFG = {
    "Verdantis Robotics": {"segment": "agri_robotics", "hq": "NL", "one_liner": "Greenhouse harvest robots on a per-hectare lease; 40 robots deployed, physical AI stack; Series B launched"},
    "Kitchenetic":        {"segment": "food_robotics", "hq": "DE", "one_liner": "Robotic kitchen for canteens and catering; automation platform, Series A in market"},
    "Helios Ferment":     {"segment": "precision_fermentation", "hq": "DE", "one_liner": "Fermentation-as-a-service platform with recurring revenue from ingredient makers; biomanufacturing scale-up"},
    "Cropline AI":        {"segment": "precision_ag_sensing", "hq": "DE", "one_liner": "Vertical AI software for agronomy with soil intelligence; ARR growing 3x"},
    "PetCell Foods":      {"segment": "cultivated_meat", "hq": "UK", "one_liner": "Cultivated chicken for pet food, approved in the UK"},
    "Terrabyte Sensors":  {"segment": "precision_ag_sensing", "hq": "AT", "one_liner": "Handheld soil sensors and agronomy app"},
    "Nordic Oat Co":      {"segment": "plant_based_meat", "hq": "SE", "one_liner": "Plant-based deli brand in Nordic retail, meat alternatives"},
    "Bergkraft Snacks":   {"segment": "organic_food_cpg_dach", "hq": "DE", "one_liner": "Organic snack brand listed in German retail"},
    "Aquaflow Hydration": {"segment": "functional_beverage_d2c", "hq": "CH", "one_liner": "Functional hydration drops, D2C to retail"},
    "MycoLeather":        {"segment": "biomaterials", "hq": "UK", "one_liner": "Mycelium leather alternative material for luxury and automotive"},
    "CocoaFree Labs":     {"segment": "alt_cocoa_ingredients", "hq": "UK", "one_liner": "Cocoa-free chocolate; sold to a strategic, earn-out running", "status_override": "exit_in_progress"},
    "FarmLedger":         {"segment": "agri_supply_chain_traceability", "hq": "ID", "one_liner": "Smallholder procurement and EUDR traceability platform, supply chain software"},
}

INVENTORY = [
    inv("Verdantis Robotics", "low", 6, items=["Pilot-to-contract conversion at 80%; Series B launched with a EUR 40m target."]),
    inv("Kitchenetic", "low", 5, items=["Series A in market; two term sheets in negotiation."]),
    inv("Helios Ferment", "low", 4, items=["Series B data room open; public co-investors in scope."]),
    inv("Cropline AI", "low", 3, items=["ARR tripled year over year; net revenue retention above 120%."]),
    inv("PetCell Foods", "low", 9, items=["Facility build on plan; 24 months of runway approved by board."]),
    inv("Terrabyte Sensors", "medium", 18, items=["Revenue flat for two quarters; product-market fit in question."]),
    inv("Nordic Oat Co", "high", 41, items=["Cash below six months; retail rotation declining."]),
    inv("Bergkraft Snacks", "medium", 25, items=["Listing fees up; margin under pressure."]),
    inv("Aquaflow Hydration", "high", 3, items=["Cash cliff; founder exploring strategic sale."]),
    inv("MycoLeather", "medium", 15, items=["Pilot with a luxury house ongoing."]),
    inv("CocoaFree Labs", "medium", 20, items=["Earn-out milestone 1 due in 14 months."]),
    inv("FarmLedger", "medium", 10, items=["Bridge decision due end of October."]),
]

F = fact  # fictional company facts: no URL, shown as internal
COMPANY_DATA = {
    "Verdantis Robotics": company("Verdantis Robotics", internal(20, "EUR 7.2m", "up", "fundraise", notes=["40 robots under lease, utilisation 78%.", "Series B launched; target EUR 40m."]),
                                  [F("Won a 12-hectare rollout with a leading Dutch tomato grower.", _d(30)), F("Harvest speed benchmark: under 30 seconds per truss.", _d(80))]),
    "Kitchenetic": company("Kitchenetic", internal(14, "EUR 3.1m", "up", "fundraise", notes=["Series A: EUR 12m target, two term sheets in negotiation."]),
                           [F("Deployed in 14 corporate canteens.", _d(40)), F("Won a national catering tender.", _d(90))]),
    "Helios Ferment": company("Helios Ferment", internal(24, "EUR 9.8m", "up", "fundraise", notes=["ARR EUR 4.1m, up 2.6x year over year.", "Gross margin 62%."]),
                              [F("Signed a multi-year capacity agreement with a top-3 ingredients group.", _d(20)), F("Named in a European deep-tech top-50 list.", _d(60), conf="medium")]),
    "Cropline AI": company("Cropline AI", internal(26, "EUR 6.5m", "up", notes=["ARR EUR 3.2m, 3x year over year."]),
                           [F("Partnership with a top-3 fertiliser company for nutrient recommendations.", _d(25)), F("Expanded to France and Poland.", _d(100))]),
    "PetCell Foods": company("PetCell Foods", internal(24, "GBP 9.5m", "flat", notes=["Facility build on plan."]),
                             [F("First retail listing for cultivated pet treats.", _d(70)), F("Regulatory approval extended to a second product.", _d(120))]),
    "Terrabyte Sensors": company("Terrabyte Sensors", internal(11, "EUR 1.9m", "flat", notes=["Revenue flat at EUR 0.4m per quarter."]),
                                 [F("Launched a subscription tier.", _d(100), direction="neutral")]),
    "Nordic Oat Co": company("Nordic Oat Co", internal(5, "SEK 6m", "down", notes=["Retail rotation down 18% year over year."]),
                             [F("Delisted from one Nordic retailer.", _d(60), direction="negative"), F("Cut headcount by a third.", _d(120), direction="negative")]),
    "Bergkraft Snacks": company("Bergkraft Snacks", internal(6.5, "EUR 0.6m", "flat", notes=["Listing fees up 20%."]),
                                [F("New listing at a discounter.", _d(50)), F("Margin pressure from cocoa and packaging costs.", _d(90), direction="negative")]),
    "Aquaflow Hydration": company("Aquaflow Hydration", internal(1.5, "CHF 0.2m", "down", "m_and_a", notes=["Sell-side mandate signed; two indications of interest."]),
                                  [F("Founder confirmed strategic-sale process publicly.", _d(30), direction="neutral"), F("Lost a key retail listing.", _d(90), direction="negative")]),
    "MycoLeather": company("MycoLeather", internal(14, "GBP 3.1m", "flat", notes=["Pilot with a luxury house."]),
                           [F("Luxury pilot extended to a second product line.", _d(40))]),
    "CocoaFree Labs": company("CocoaFree Labs", internal(None, None, "unknown", "none", notes=["Exit signed; earn-out milestones tracked."]), []),
    "FarmLedger": company("FarmLedger", internal(4, "USD 0.5m", "up", "bridge", deadline=_d(-45), notes=["Bridge of USD 1.5m under discussion; decision due 2026-10-23."]),
                          [F("Onboarded 12,000 smallholders.", _d(60)), F("EUDR pilot with a European buyer.", _d(100))]),
}

MACRO = {
    "facts": [fact("Physical AI companies raised about $47bn in H1 2026.", "2026-07", url=PHYS_AI),
              fact("Accel raised $5bn for late-stage bets with robotics among the named focus areas.", "2026-04-15", url=ACCEL_FUND),
              fact("More than 80 plant-based companies were acquired, merged or shut down since September 2024.", "2026-07", url=NOSH_CONSOL, direction="negative"),
              fact("Government-backed funds are leading deep-tech biotech Series B rounds in Europe.", "2026-03-31", url=SO_SERIES_B, direction="neutral")],
    "interest_rate_direction": "tightening",
    "venture_funding_direction": "improving",
    "agrifood_funding_direction": "flat",
    "summary": "Capital is flowing to physical AI and robotics at record levels, with Accel's $5bn late-stage fund naming robotics explicitly. Deep-tech biotech in Europe is increasingly led by public and bank-backed funds. Consumer plant-based brands are consolidating into a few platforms. Read: robotics companies with traction can raise from growth funds; weak consumer brands should talk to consolidators early.",
}


def build() -> tuple[list[dict], dict, dict, dict, dict, date]:
    return INVENTORY, COMPANIES_CFG, load_segments(), COMPANY_DATA, MACRO, AS_OF
