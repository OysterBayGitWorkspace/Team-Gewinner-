"""Illustrative demo data for showcasing the Portfolio Market Pulse without confidential information.

Every company, number, cash position and internal note below is fictional. Funds and corporates
are real, public entities; the deals and quotes attributed to them here are illustrative and must
not be cited as facts. The scoring engine and the rules are the real ones.
"""
from __future__ import annotations

from datetime import date, timedelta

AS_OF = date(2026, 9, 8)


def _d(days_ago: int) -> str:
    return (AS_OF - timedelta(days=days_ago)).isoformat()


def fact(claim, days_ago, direction="positive", conf="high", url="https://example.org/demo-source"):
    return {"claim": claim, "date": _d(days_ago), "direction": direction, "source_url": url, "source_type": "web", "confidence": conf}


def party(name, evidence, days_ago, intent="acted", kw=(), url="https://example.org/demo-source"):
    return {"name": name, "evidence": evidence, "date": _d(days_ago), "source_url": url, "intent": intent, "mandate_keywords": list(kw)}


def deal(target, acquirer, kind, days_ago, value=None):
    return {"target": target, "acquirer_or_lead": acquirer, "kind": kind, "date": _d(days_ago), "value": value, "source_url": "https://example.org/demo-source"}


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


# ---- segments (fictional evidence, real public names) ----
SEGMENTS = {
    "precision_fermentation": segment(
        "precision_fermentation",
        funding=[fact("Fermentation platform Series B rounds in Europe totalled roughly €410m in the last 12 months, up about 60% year over year.", 30),
                 fact("Two European biomanufacturing platforms closed rounds above €80m in the last quarter, both led by growth funds.", 45),
                 fact("Median Series B size in precision fermentation rose to about €45m.", 90, conf="medium")],
        funds=[party("Accel", "Led a €95m Series B in a European fermentation-as-a-service platform; partner said the firm is 'actively looking for AI-driven biomanufacturing platforms with recurring revenue in Europe'.", 40, "stated_looking_for", ["biomanufacturing", "fermentation", "platform", "recurring revenue", "Series B"]),
               party("Index Ventures", "Co-led a €60m growth round for a fermentation ingredients company.", 120),
               party("Astanor", "Joined two fermentation rounds in the last nine months.", 200),
               party("Lowercarbon Capital", "Closed a new $550m fund with a stated mandate including 'industrial biology and biomanufacturing'.", 70, "stated_looking_for", ["biomanufacturing", "industrial biology", "climate"])],
        reg=[fact("EU Biotech Act proposal includes fast-track approval lanes for fermentation-derived food ingredients.", 60),
             fact("EFSA cleared three fermentation-derived protein applications in the last 18 months.", 150)],
        players=[party("DSM-Firmenich", "CEO said on the Q2 call the group 'wants to add platform capabilities in precision fermentation, including through M&A'.", 50, "stated_looking_for", ["precision fermentation", "platform", "M&A"]),
                 party("Novonesis", "Signed a co-development and capacity partnership with a fermentation startup.", 100)],
        deals=[deal("FermCo A", "Kerry", "acquisition", 220, "€310m"), deal("FermCo B", "Index Ventures", "growth_round", 130, "€60m")],
        cons=[party("Liberation Bio Holdings", "Buy-and-build of contract fermentation capacity; two acquisitions in 14 months.", 90)]),

    "agri_robotics": segment(
        "agri_robotics",
        funding=[fact("Agricultural robotics raised about $1.1bn globally in the last 12 months, the strongest year since 2021.", 40),
                 fact("Harvest-automation companies closed six rounds above $30m in the last year.", 80)],
        funds=[party("Accel", "Led a $70m Series B in a European greenhouse automation company; the firm's 'physical AI' thesis names agriculture as a priority.", 60, "stated_looking_for", ["robotics", "physical AI", "agriculture", "automation", "Series B"]),
               party("Eclipse Ventures", "Led a $45m round in a field robotics company.", 150),
               party("Prosus Ventures", "Joined a $50m harvest robotics round.", 100)],
        reg=[fact("Netherlands tightened seasonal-labour rules for greenhouses, raising labour cost pressure.", 120),
             fact("EU machinery regulation transition period confirmed, no new barriers for autonomous field robots.", 200, direction="neutral", conf="medium")],
        players=[party("Kubota", "Announced a $300m corporate venture allocation for 'autonomy and agricultural robotics'.", 45, "stated_looking_for", ["robotics", "autonomy", "agriculture"]),
                 party("John Deere", "Acquired a greenhouse robotics startup.", 300)],
        deals=[deal("RoboGrow", "John Deere", "acquisition", 300, "$250m"), deal("Harvestly", "Accel", "growth_round", 60, "$70m")],
        cons=[]),

    "precision_ag_sensing": segment(
        "precision_ag_sensing",
        funding=[fact("Farm software and sensing raised about $900m in the last 12 months.", 30), fact("Three agri-data platforms closed growth rounds above $40m.", 100)],
        funds=[party("Accel", "Partner blog post: 'we are looking for vertical AI software in agriculture with proven ARR growth'.", 25, "stated_looking_for", ["vertical AI", "agriculture", "software", "ARR"]),
               party("Anterra Capital", "Led two agri-software rounds in the last year.", 110),
               party("Insight Partners", "Joined a $55m agronomy platform round.", 180)],
        reg=[fact("EU soil monitoring law adopted, creating demand for field-level soil data.", 90), fact("CAP 2028 draft rewards measured nutrient efficiency.", 140)],
        players=[party("Yara", "Head of digital farming said Yara 'is looking to partner with or acquire soil-intelligence companies'.", 70, "stated_looking_for", ["soil", "digital farming", "acquire"]),
                 party("Bayer Crop Science", "Integrated a third-party soil sensing startup into its platform.", 160)],
        deals=[deal("SoilIQ", "CropX", "acquisition", 200), deal("AgroData", "Yara", "acquisition", 400, "$120m")],
        cons=[party("CropX", "Seven acquisitions since 2020, CEO calls the company 'an M&A machine'.", 200)]),

    "plant_based_meat": segment(
        "plant_based_meat",
        funding=[fact("Plant-based meat funding fell about 35% year over year.", 60, direction="negative"),
                 fact("Two European plant-based brands closed down-rounds in the last six months.", 90, direction="negative"),
                 fact("Category retail sales in Germany stabilised after two years of decline.", 120, direction="neutral", conf="medium")],
        funds=[party("Blue Horizon", "Led an insider extension round.", 150)],
        reg=[fact("EU meaty-names labelling ban deferred.", 100, direction="neutral"), fact("France naming decree upheld.", 200, direction="negative")],
        players=[party("Nestlé", "Divested a plant-based brand.", 250, "acted")],
        deals=[deal("VeggieCo", "Plantbound Holdings", "acquisition", 120), deal("GreenPatty", "Plantbound Holdings", "merger", 200), deal("Oatish", None or "n/a", "shutdown", 90)],
        cons=[party("Plantbound Holdings", "Buy-and-build platform for plant-based brands; four acquisitions in 24 months, stated aim of 'a European house of plant-based brands'.", 120, "stated_looking_for", ["plant-based", "brands", "consolidation", "Europe"]),
              party("Vion Food Group", "Rolled two plant-based lines into its own portfolio.", 240)]),

    "organic_food_cpg_dach": segment(
        "organic_food_cpg_dach",
        funding=[fact("DACH food brand funding is at a five-year low.", 60, direction="negative"), fact("Retail listing fees rose again in 2026.", 100, direction="negative", conf="medium")],
        funds=[],
        reg=[fact("Werbeverbot for children's food advertising passed.", 150, direction="negative"), fact("EU organic regulation stable.", 300, direction="neutral")],
        players=[party("Katjes International", "Said it is 'actively looking for organic brands with proven retail rotation in Germany'.", 40, "stated_looking_for", ["organic", "brands", "Germany", "retail"])],
        deals=[deal("BioSnackz", "Katjes International", "acquisition", 180), deal("Kindermüsli GmbH", "Hochland", "acquisition", 350)],
        cons=[party("Katjes International", "Serial acquirer of DACH food brands; three deals in 24 months.", 180, "stated_looking_for", ["organic", "brands", "Germany"]),
              party("Holle Holding", "Consolidating organic baby-food brands.", 260)]),

    "functional_beverage_d2c": segment(
        "functional_beverage_d2c",
        funding=[fact("Functional beverage rounds up 40% year over year.", 30), fact("Hydration brands closed five rounds above $20m.", 80)],
        funds=[party("VMG Partners", "Led a $30m hydration brand round.", 120)],
        reg=[fact("EU health-claims tightening for electrolyte products.", 90, direction="negative"), fact("Sugar tax extended in two EU markets.", 200, direction="negative")],
        players=[party("Danone", "Completed a large functional-nutrition acquisition.", 4), party("PepsiCo", "Stated push into functional hydration.", 200, "stated_looking_for", ["hydration", "functional"]),
                 party("Nestlé", "JV with Platinum Equity to consolidate water and hydration brands.", 45, "stated_looking_for", ["hydration", "water", "brands"])],
        deals=[deal("Huel-like", "Danone", "acquisition", 4, "$1.2bn"), deal("EMPWR-like", "Vitamin Well Group", "acquisition", 60)],
        cons=[party("Nestlé / Platinum Equity JV", "Explicit inorganic growth mandate in hydration.", 45, "stated_looking_for", ["hydration", "beverage"]),
              party("Vitamin Well Group", "PE-backed roll-up of functional nutrition brands.", 60)]),

    "cultivated_meat": segment(
        "cultivated_meat",
        funding=[fact("Cultivated meat funding recovered modestly, led by pet-food applications.", 60, conf="medium"), fact("Two insider-led rounds above $20m.", 120, direction="neutral")],
        funds=[party("Agronomics", "Led a pet-food cultivated meat round.", 100), party("Clean Growth Fund", "Joined the same round.", 100), party("Mars Petcare Ventures", "Invested in a cultivated pet-food company.", 200)],
        reg=[fact("UK FSA sandbox approvals progressing.", 90), fact("EU Novel Food timelines unchanged.", 200, direction="neutral")],
        players=[party("Mars Petcare", "Said it is 'looking for cultivated protein partners for pet food'.", 80, "stated_looking_for", ["cultivated", "pet food", "protein"]),
                 party("Nestlé Purina", "Pilot partnership announced.", 150)],
        deals=[deal("CellPet", "Mars Petcare", "acquisition", 300), deal("MeatMerge", "PARIMA", "merger", 330)],
        cons=[party("PARIMA", "Merged two cultivated meat companies.", 330), party("Fork & Good", "Acquired a peer.", 310)]),

    "biomaterials": segment(
        "biomaterials",
        funding=[fact("Next-gen materials funding flat year over year.", 60, direction="neutral"), fact("One large round above $50m in the last quarter.", 40)],
        funds=[party("Sofinnova Partners", "Led a biomaterials round.", 250), party("Brightlands Venture Partners", "Joined.", 250)],
        reg=[fact("EU Ecodesign rules favour bio-based materials.", 120), fact("Green Claims directive adds compliance cost.", 200, direction="negative", conf="medium")],
        players=[party("Kering", "Said it is 'looking for scalable leather alternatives'.", 100, "stated_looking_for", ["leather", "material", "alternative"])],
        deals=[deal("LeatherX", "Lenzing", "acquisition", 400)],
        cons=[]),

    "food_robotics": segment(
        "food_robotics",
        funding=[fact("Kitchen robotics funding doubled year over year.", 30), fact("Largest food-robotics round on record closed last quarter.", 50)],
        funds=[party("Accel", "Participated in a large food-tech automation round.", 60), party("Kleiner Perkins", "Partner: 'robotics is the ultimate frontier'.", 90, "stated_looking_for", ["robotics", "automation"]), party("HCVC", "Hard-tech fund active in the segment.", 200)],
        reg=[fact("EU AI Act transition confirmed.", 150, direction="neutral"), fact("Minimum wage increase in Germany raises automation demand.", 60)],
        players=[party("Circus SE", "Serial acquirer of kitchen robotics IP.", 60), party("Compass Group", "Deploying robotic kiosks at scale.", 120), party("Sodexo", "Partnership.", 100)],
        deals=[deal("K-Robotics", "Circus SE", "acquisition", 130), deal("Alberts", "Circus SE", "acquisition", 68)],
        cons=[party("Circus SE", "Two acquisitions in 14 months.", 68), party("Miso Robotics", "Acquired patents and assets of two peers.", 90)]),

    "alt_cocoa_ingredients": segment(
        "alt_cocoa_ingredients",
        funding=[fact("Cocoa-free chocolate funding active on the back of cocoa prices.", 60), fact("Two rounds above €20m.", 90)],
        funds=[party("World Fund", "Led a cocoa-alternative round.", 120)],
        reg=[fact("EUDR timeline confirmed.", 100)],
        players=[party("Döhler", "Acquired a cocoa-free chocolate company.", 165), party("Barry Callebaut", "Partnership with an alternative-cocoa startup.", 200)],
        deals=[deal("Nukoko-like", "Döhler", "acquisition", 165)],
        cons=[]),

    "agri_supply_chain_traceability": segment(
        "agri_supply_chain_traceability",
        funding=[fact("Traceability software raised about $600m in 12 months on EUDR demand.", 40), fact("Compliance platforms closed three growth rounds.", 90)],
        funds=[party("S2G Investments", "Closed a $1bn fund with a mandate including supply chains.", 120, "stated_looking_for", ["supply chain", "agriculture", "systems"]), party("Icos Capital", "Led a Series A.", 300), party("Rabo Investments", "Joined.", 300)],
        reg=[fact("EUDR enforcement starts, with a simplification package.", 60), fact("Indonesia palm export levy adjusted.", 150, direction="neutral", conf="medium")],
        players=[party("Cargill", "Co-founded a compliance platform.", 300), party("Olam", "Same.", 300), party("Unilever", "Said it 'seeks traceability partners for smallholder sourcing'.", 50, "stated_looking_for", ["traceability", "smallholder", "sourcing"])],
        deals=[deal("farmer connect-like", "Agridence", "acquisition", 380), deal("TraceCo", "Cargill", "acquisition", 200)],
        cons=[party("Agridence", "Built a compliance platform through acquisitions.", 380), party("CropX", "Acquisitive.", 200)]),
}

# ---- fictional companies ----
COMPANIES_CFG = {
    "Helios Ferment":     {"segment": "precision_fermentation", "hq": "DE", "one_liner": "Fermentation-as-a-service platform with recurring revenue from ingredient makers; Series B ready"},
    "Verdantis Robotics": {"segment": "agri_robotics", "hq": "NL", "one_liner": "Greenhouse harvest robots on a per-hectare lease; 40 robots deployed, physical AI stack"},
    "Cropline AI":        {"segment": "precision_ag_sensing", "hq": "DE", "one_liner": "Vertical AI software for agronomy with soil intelligence; ARR growing 3x"},
    "Kitchenetic":        {"segment": "food_robotics", "hq": "DE", "one_liner": "Robotic kitchen for canteens and catering; raising a Series A"},
    "PetCell Foods":      {"segment": "cultivated_meat", "hq": "UK", "one_liner": "Cultivated chicken for pet food, approved in the UK"},
    "Terrabyte Sensors":  {"segment": "precision_ag_sensing", "hq": "AT", "one_liner": "Handheld soil sensors and agronomy app"},
    "Nordic Oat Co":      {"segment": "plant_based_meat", "hq": "SE", "one_liner": "Plant-based deli brand in Nordic retail"},
    "Bergkraft Snacks":   {"segment": "organic_food_cpg_dach", "hq": "DE", "one_liner": "Organic snack brand listed in German retail"},
    "Aquaflow Hydration": {"segment": "functional_beverage_d2c", "hq": "CH", "one_liner": "Hydration drops, D2C to retail"},
    "MycoLeather":        {"segment": "biomaterials", "hq": "UK", "one_liner": "Mycelium leather alternative for luxury and automotive"},
    "CocoaFree Labs":     {"segment": "alt_cocoa_ingredients", "hq": "UK", "one_liner": "Cocoa-free chocolate; sold to a strategic, earn-out running", "status_override": "exit_in_progress"},
    "FarmLedger":         {"segment": "agri_supply_chain_traceability", "hq": "ID", "one_liner": "Smallholder procurement and EUDR traceability platform in Indonesia"},
}

INVENTORY = [
    inv("Helios Ferment", "low", 4, items=["Series B data room open; two term sheets expected in Q4."]),
    inv("Verdantis Robotics", "low", 6, items=["Pilot-to-contract conversion at 80%; hiring plan on budget."]),
    inv("Cropline AI", "low", 3, items=["ARR tripled year over year; net revenue retention above 120%."]),
    inv("Kitchenetic", "medium", 12, items=["Series A in market; founders actively raising."]),
    inv("PetCell Foods", "low", 9, items=["Facility build on plan; 24 months of runway approved by board."]),
    inv("Terrabyte Sensors", "medium", 18, items=["Revenue flat for two quarters; product-market fit in question."]),
    inv("Nordic Oat Co", "high", 41, items=["Cash below six months; retail rotation declining."]),
    inv("Bergkraft Snacks", "medium", 25, items=["Listing fees up; margin under pressure."]),
    inv("Aquaflow Hydration", "high", 3, items=["Cash cliff; founder exploring strategic sale."]),
    inv("MycoLeather", "medium", 15, items=["Pilot with a luxury house ongoing."]),
    inv("CocoaFree Labs", "medium", 20, items=["Earn-out milestone 1 due in 14 months."]),
    inv("FarmLedger", "medium", 10, items=["Bridge decision due end of October."]),
]

COMPANY_DATA = {
    "Helios Ferment": company("Helios Ferment", internal(24, "EUR 9.8m", "up", "fundraise", notes=["ARR EUR 4.1m, up 2.6x year over year (fictional).", "Gross margin 62%."]),
                              [fact("Signed a multi-year capacity agreement with a top-3 ingredients group.", 20), fact("Named in a European deep-tech top-50 list.", 60, conf="medium")]),
    "Verdantis Robotics": company("Verdantis Robotics", internal(20, "EUR 7.2m", "up", "fundraise", notes=["40 robots under lease, utilisation 78%.", "Series B launched; target EUR 40m."]),
                                  [fact("Won a 12-hectare rollout with a leading Dutch tomato grower.", 30), fact("Harvest speed benchmark published: under 30 seconds per truss.", 80)]),
    "Cropline AI": company("Cropline AI", internal(26, "EUR 6.5m", "up", notes=["ARR EUR 3.2m, 3x year over year."]),
                           [fact("Partnership with a top-3 fertiliser company for nutrient recommendations.", 25), fact("Expanded to France and Poland.", 100)]),
    "Kitchenetic": company("Kitchenetic", internal(9, "EUR 2.1m", "up", "fundraise", notes=["Series A: EUR 12m target, first term sheet in negotiation."]),
                           [fact("Deployed in 14 corporate canteens.", 40), fact("Won a national catering tender.", 90)]),
    "PetCell Foods": company("PetCell Foods", internal(24, "GBP 9.5m", "flat", notes=["Facility build on plan."]),
                             [fact("First retail listing for cultivated pet treats.", 70), fact("Regulatory approval extended to a second product.", 120)]),
    "Terrabyte Sensors": company("Terrabyte Sensors", internal(11, "EUR 1.9m", "flat", notes=["Revenue flat at EUR 0.4m per quarter."]),
                                 [fact("Launched a subscription tier.", 100, direction="neutral")]),
    "Nordic Oat Co": company("Nordic Oat Co", internal(5, "SEK 6m", "down", notes=["Retail rotation down 18% year over year."]),
                             [fact("Delisted from one Nordic retailer.", 60, direction="negative"), fact("Cut headcount by a third.", 120, direction="negative")]),
    "Bergkraft Snacks": company("Bergkraft Snacks", internal(6.5, "EUR 0.6m", "flat", notes=["Listing fees up 20%."]),
                                [fact("New listing at a discounter.", 50), fact("Margin pressure from cocoa and packaging costs.", 90, direction="negative")]),
    "Aquaflow Hydration": company("Aquaflow Hydration", internal(1.5, "CHF 0.2m", "down", "m_and_a", notes=["Sell-side mandate signed; two indications of interest."]),
                                  [fact("Founder confirmed strategic-sale process publicly.", 30, direction="neutral"), fact("Lost a key retail listing.", 90, direction="negative")]),
    "MycoLeather": company("MycoLeather", internal(14, "GBP 3.1m", "flat", notes=["Pilot with a luxury house."]),
                           [fact("Luxury pilot extended to a second product line.", 40)]),
    "CocoaFree Labs": company("CocoaFree Labs", internal(None, None, "unknown", "none", notes=["Exit signed; earn-out milestones tracked."]), []),
    "FarmLedger": company("FarmLedger", internal(4, "USD 0.5m", "up", "bridge", deadline=_d(-45), notes=["Bridge of USD 1.5m under discussion; decision due 2026-10-23."]),
                          [fact("Onboarded 12,000 smallholders.", 60), fact("EUDR pilot with a European buyer.", 100)]),
}

MACRO = {
    "facts": [fact("ECB held rates at 2.25% in September; markets price one more hike.", 5, direction="negative"),
              fact("Global VC funding in H1 2026 at a five-year high, concentrated in AI and physical AI.", 40),
              fact("Agrifood-tech deal counts at eight-year lows even as capital concentrates in fewer, larger rounds.", 45, direction="negative"),
              fact("Exit value in Q2 2026 exceeded the 2021 full-year record.", 50)],
    "interest_rate_direction": "tightening",
    "venture_funding_direction": "improving",
    "agrifood_funding_direction": "flat",
    "summary": "Illustrative macro read. Rates are tightening, venture funding is recovering but concentrated in AI and physical AI, agrifood deal counts are thin while a few large rounds close, and the exit window is open for category leaders. Weak brands in consumer categories face consolidation.",
}


EXTRA_SEGMENT_LABELS = {
    "precision_fermentation": {"label": "Precision fermentation and biomanufacturing platforms",
                               "keywords": ["precision fermentation", "biomanufacturing", "fermentation platform", "recurring revenue"]},
}


def build() -> tuple[list[dict], dict, dict, dict, dict, date]:
    return INVENTORY, COMPANIES_CFG, SEGMENTS, COMPANY_DATA, MACRO, AS_OF
