"""JSON schemas for every worker output.

Workers are LLM processes. Nothing they return is trusted until it validates
against one of these schemas. Scoring only reads schema fields, never prose.
"""

FACT = {
    "type": "object",
    "properties": {
        "claim": {"type": "string", "maxLength": 400},
        "date": {"type": ["string", "null"], "description": "YYYY-MM-DD or YYYY-MM when known, else null"},
        "direction": {"type": "string", "enum": ["positive", "negative", "neutral"]},
        "source_url": {"type": ["string", "null"]},
        "source_type": {"type": "string", "enum": ["web", "jarvis"]},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["claim", "date", "direction", "source_url", "source_type", "confidence"],
    "additionalProperties": False,
}

INVENTORY = {
    "type": "object",
    "properties": {
        "as_of": {"type": "string"},
        "companies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "org_id": {"type": ["string", "null"]},
                    "status": {"type": "string"},
                    "funds": {"type": "array", "items": {"type": "string"}},
                    "risk_band": {"type": ["string", "null"], "enum": ["high", "medium", "low", None]},
                    "risk_score": {"type": ["number", "null"]},
                    "days_since_contact": {"type": ["integer", "null"]},
                    "attention_items": {"type": "array", "items": {"type": "string", "maxLength": 600}},
                    "coverage_notes": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "org_id", "status", "funds", "risk_band", "risk_score",
                             "days_since_contact", "attention_items", "coverage_notes"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["as_of", "companies"],
    "additionalProperties": False,
}

MACRO = {
    "type": "object",
    "properties": {
        "facts": {"type": "array", "items": FACT},
        "interest_rate_direction": {"type": "string", "enum": ["easing", "flat", "tightening", "unknown"]},
        "venture_funding_direction": {"type": "string", "enum": ["improving", "flat", "deteriorating", "unknown"]},
        "agrifood_funding_direction": {"type": "string", "enum": ["improving", "flat", "deteriorating", "unknown"]},
        "summary": {"type": "string", "maxLength": 800},
    },
    "required": ["facts", "interest_rate_direction", "venture_funding_direction",
                 "agrifood_funding_direction", "summary"],
    "additionalProperties": False,
}

_NAMED_EVIDENCE = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "evidence": {"type": "string", "maxLength": 300},
        "date": {"type": ["string", "null"]},
        "source_url": {"type": ["string", "null"]},
        "intent": {"type": "string", "enum": ["stated_looking_for", "acted"],
                   "description": "stated_looking_for = they publicly said what they want to invest in / acquire / partner on; acted = they did a deal"},
        "mandate_keywords": {"type": "array", "items": {"type": "string", "maxLength": 40}, "maxItems": 8,
                             "description": "3 to 8 keywords from their own words describing what they look for (e.g. 'alt protein', 'B2B ingredients', 'Series B', 'DACH'). Empty if intent is acted."},
    },
    "required": ["name", "evidence", "date", "source_url", "intent", "mandate_keywords"],
    "additionalProperties": False,
}

_DEAL = {
    "type": "object",
    "properties": {
        "target": {"type": "string"},
        "acquirer_or_lead": {"type": "string"},
        "kind": {"type": "string", "enum": ["acquisition", "merger", "growth_round", "shutdown", "other"]},
        "date": {"type": ["string", "null"]},
        "value": {"type": ["string", "null"]},
        "source_url": {"type": ["string", "null"]},
    },
    "required": ["target", "acquirer_or_lead", "kind", "date", "value", "source_url"],
    "additionalProperties": False,
}

SEGMENT = {
    "type": "object",
    "properties": {
        "segment_id": {"type": "string"},
        "funding_market": {"type": "object", "properties": {"facts": {"type": "array", "items": FACT}},
                           "required": ["facts"], "additionalProperties": False},
        "capital_access": {
            "type": "object",
            "properties": {
                "facts": {"type": "array", "items": FACT},
                "active_funds": {"type": "array", "items": _NAMED_EVIDENCE,
                                 "description": "Growth or specialist funds that led or joined a round in this segment in the last 12 months"},
            },
            "required": ["facts", "active_funds"], "additionalProperties": False,
        },
        "regulation": {"type": "object", "properties": {"facts": {"type": "array", "items": FACT}},
                       "required": ["facts"], "additionalProperties": False},
        "strategics": {
            "type": "object",
            "properties": {
                "facts": {"type": "array", "items": FACT},
                "players": {"type": "array", "items": _NAMED_EVIDENCE,
                            "description": "Corporates that publicly said what they look for, invested, partnered or acquired in this segment in the last 12 months"},
            },
            "required": ["facts", "players"], "additionalProperties": False,
        },
        "exit_comps": {
            "type": "object",
            "properties": {
                "facts": {"type": "array", "items": FACT},
                "deals": {"type": "array", "items": _DEAL},
            },
            "required": ["facts", "deals"], "additionalProperties": False,
        },
        "consolidators": {
            "type": "object",
            "properties": {
                "facts": {"type": "array", "items": FACT},
                "players": {"type": "array", "items": _NAMED_EVIDENCE,
                            "description": "PE platforms, roll-up vehicles, buy-and-build holdings and well-funded peers that bought or merged two or more companies in this segment in the last 24 months, or publicly announced a consolidation strategy"},
            },
            "required": ["facts", "players"], "additionalProperties": False,
        },
    },
    "required": ["segment_id", "funding_market", "capital_access", "regulation", "strategics", "exit_comps", "consolidators"],
    "additionalProperties": False,
}

COMPANY = {
    "type": "object",
    "properties": {
        "company": {"type": "string"},
        "internal": {
            "type": "object",
            "properties": {
                "runway_months": {"type": ["number", "null"]},
                "runway_as_of": {"type": ["string", "null"]},
                "cash": {"type": ["string", "null"], "description": "Latest cash with currency, e.g. 'EUR 1.2m'"},
                "cash_as_of": {"type": ["string", "null"]},
                "kpi_trend": {"type": "string", "enum": ["up", "flat", "down", "unknown"]},
                "active_process": {"type": "string", "enum": ["fundraise", "m_and_a", "bridge", "wind_down", "none", "unknown"]},
                "process_deadline": {"type": ["string", "null"], "description": "YYYY-MM-DD if a decision or cash-out date is documented"},
                "data_status": {"type": "string", "enum": ["ok", "partial", "jarvis_error", "no_data"]},
                "notes": {"type": "array", "items": {"type": "string", "maxLength": 400}},
            },
            "required": ["runway_months", "runway_as_of", "cash", "cash_as_of", "kpi_trend",
                         "active_process", "process_deadline", "data_status", "notes"],
            "additionalProperties": False,
        },
        "external_facts": {"type": "array", "items": FACT},
        "segment_check": {"type": "string", "maxLength": 300,
                          "description": "One line: does the curated segment fit what the company does? Say 'fits' or propose a better segment id."},
    },
    "required": ["company", "internal", "external_facts", "segment_check"],
    "additionalProperties": False,
}
