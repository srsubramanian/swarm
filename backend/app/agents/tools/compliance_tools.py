"""Compliance domain tools — sanctions, transaction history, regulatory thresholds.

All tools return simulated mock data keyed on the 4 built-in scenarios.
Interfaces are designed for easy swap to real implementations later.
"""

import json

from langchain_core.tools import tool


@tool
def search_sanctions_list(name: str, country: str) -> str:
    """Search OFAC, EU, and UN sanctions lists for a person or entity.

    Args:
        name: Name of the person or entity to search.
        country: Two-letter country code (e.g. CY, TR, US).

    Returns:
        JSON string with sanctions search results including match score,
        jurisdiction risk, and FATF status.
    """
    country = country.upper()

    # Country-keyed mock data
    results_by_country = {
        "CY": {
            "matches": [
                {
                    "list": "EU Consolidated",
                    "matched_name": "Meridian Holdings Ltd (Cyprus)",
                    "score": 0.72,
                    "match_type": "partial_name",
                    "status": "active",
                }
            ],
            "jurisdiction_risk": "medium",
            "fatf_status": "monitored",
            "notes": "Cyprus is an EU member but has elevated AML risk due to historical shell company activity.",
        },
        "TR": {
            "matches": [],
            "jurisdiction_risk": "elevated",
            "fatf_status": "grey_list",
            "notes": "Turkey is on the FATF grey list. Enhanced due diligence required for transactions.",
        },
        "IR": {
            "matches": [
                {
                    "list": "OFAC SDN",
                    "matched_name": name,
                    "score": 0.95,
                    "match_type": "exact",
                    "status": "active",
                }
            ],
            "jurisdiction_risk": "critical",
            "fatf_status": "black_list",
            "notes": "Iran is under comprehensive OFAC sanctions. Transaction must be blocked.",
        },
    }

    result = results_by_country.get(
        country,
        {
            "matches": [],
            "jurisdiction_risk": "low",
            "fatf_status": "compliant",
            "notes": f"No sanctions matches found for '{name}' in {country}.",
        },
    )

    result["searched_name"] = name
    result["searched_country"] = country
    result["match_count"] = len(result["matches"])
    return json.dumps(result, indent=2)


@tool
def get_client_transaction_history(client_name: str) -> str:
    """Retrieve recent transaction history and patterns for a client.

    Args:
        client_name: Name of the client to look up.

    Returns:
        JSON string with transaction history, account age, risk rating,
        and pattern analysis.
    """
    histories = {
        "Meridian Holdings": {
            "account_age_years": 6,
            "risk_rating": "medium",
            "average_monthly_volume": 850_000,
            "recent_transactions": [
                {"date": "2026-02-15", "type": "wire_transfer", "amount": 1_200_000, "destination": "DE", "status": "cleared"},
                {"date": "2026-02-01", "type": "wire_transfer", "amount": 950_000, "destination": "NL", "status": "cleared"},
                {"date": "2026-01-18", "type": "wire_transfer", "amount": 780_000, "destination": "CY", "status": "cleared_after_edd"},
            ],
            "flags": ["cyprus_transfers_previously_cleared", "volume_trending_up"],
            "notes": "Client has established pattern of EU trade finance transfers. January Cyprus transfer required EDD but was cleared.",
        },
        "Riverside Deli LLC": {
            "account_age_years": 3,
            "risk_rating": "low",
            "average_monthly_volume": 18_000,
            "recent_transactions": [
                {"date": "2026-02-27", "type": "cash_deposit", "amount": 9_500, "branch": "Main St #042", "status": "completed"},
                {"date": "2026-02-28", "type": "cash_deposit", "amount": 9_700, "branch": "Main St #042", "status": "completed"},
                {"date": "2026-02-20", "type": "cash_deposit", "amount": 4_200, "branch": "Main St #042", "status": "completed"},
            ],
            "flags": ["sudden_volume_increase", "deposits_near_ctr_threshold"],
            "notes": "Cash deposits have tripled vs. historical average. All recent deposits just below $10,000 CTR threshold.",
        },
        "Quantum Dynamics": {
            "account_age_years": 4,
            "risk_rating": "low",
            "average_monthly_volume": 920_000,
            "recent_transactions": [
                {"date": "2026-02-28", "type": "batch_ach", "amount": 875_000, "count": 42, "status": "completed"},
                {"date": "2026-01-31", "type": "batch_ach", "amount": 910_000, "count": 45, "status": "completed"},
                {"date": "2025-12-31", "type": "batch_ach", "amount": 890_000, "count": 43, "status": "completed"},
            ],
            "flags": [],
            "notes": "Consistent payroll processor. Monthly batch ACH is well-established pattern. Current transaction count (47) within normal range.",
        },
        "Atlas Capital": {
            "account_age_years": 7,
            "risk_rating": "medium",
            "average_monthly_volume": 5_200_000,
            "recent_transactions": [
                {"date": "2026-02-28", "type": "wire_transfer", "amount": 3_100_000, "destination": "GB", "status": "cleared"},
                {"date": "2026-02-15", "type": "wire_transfer", "amount": 2_800_000, "destination": "HK", "status": "cleared"},
            ],
            "flags": ["high_value_client", "international_exposure"],
            "notes": "US-based hedge fund with significant international wire activity. All transactions have been from NYC.",
        },
    }

    result = histories.get(
        client_name,
        {
            "account_age_years": 0,
            "risk_rating": "unknown",
            "average_monthly_volume": 0,
            "recent_transactions": [],
            "flags": [],
            "notes": f"No transaction history found for client '{client_name}'.",
        },
    )

    result["client_name"] = client_name
    return json.dumps(result, indent=2)


@tool
def check_regulatory_thresholds(event_type: str, amount: float, jurisdiction: str) -> str:
    """Check if a transaction triggers regulatory reporting thresholds.

    Args:
        event_type: Type of event (e.g. wire_transfer, cash_deposit, batch_ach).
        amount: Transaction amount in USD.
        jurisdiction: Two-letter country code for the destination jurisdiction.

    Returns:
        JSON string with applicable thresholds, triggered rules, and
        required actions.
    """
    jurisdiction = jurisdiction.upper()
    triggered_rules = []
    required_actions = []

    # CTR threshold for cash
    if event_type == "cash_deposit" and amount >= 10_000:
        triggered_rules.append({
            "rule": "CTR_FILING",
            "regulation": "BSA 31 CFR 1010.311",
            "threshold": 10_000,
            "description": "Currency Transaction Report required for cash transactions over $10,000.",
        })
        required_actions.append("File CTR within 15 days")

    # Structuring detection
    if event_type == "cash_deposit" and 8_000 <= amount < 10_000:
        triggered_rules.append({
            "rule": "STRUCTURING_SUSPICION",
            "regulation": "BSA 31 USC 5324",
            "threshold": 10_000,
            "description": f"Transaction of ${amount:,.0f} is just below CTR threshold. Review for potential structuring.",
        })
        required_actions.append("Review for structuring pattern — consider SAR filing")

    # Large wire EDD
    if event_type == "wire_transfer" and amount >= 1_000_000:
        triggered_rules.append({
            "rule": "LARGE_WIRE_EDD",
            "regulation": "FATF Recommendation 16 / BSA",
            "threshold": 1_000_000,
            "description": f"Wire transfer of ${amount:,.0f} exceeds enhanced due diligence threshold.",
        })
        required_actions.append("Enhanced due diligence review required")

    # FATF grey list check
    fatf_grey_list = {"TR", "MM", "PH", "SY", "YE", "HT", "JM", "PA"}
    fatf_black_list = {"IR", "KP"}

    if jurisdiction in fatf_black_list:
        triggered_rules.append({
            "rule": "FATF_BLACK_LIST",
            "regulation": "FATF Public Statement",
            "threshold": 0,
            "description": f"Jurisdiction {jurisdiction} is on FATF black list. Transaction should be blocked.",
        })
        required_actions.append("Block transaction — FATF black list jurisdiction")
    elif jurisdiction in fatf_grey_list:
        triggered_rules.append({
            "rule": "FATF_GREY_LIST",
            "regulation": "FATF Increased Monitoring",
            "threshold": 0,
            "description": f"Jurisdiction {jurisdiction} is under FATF increased monitoring.",
        })
        required_actions.append("Apply enhanced due diligence for grey-list jurisdiction")

    result = {
        "event_type": event_type,
        "amount": amount,
        "jurisdiction": jurisdiction,
        "rules_triggered": len(triggered_rules),
        "triggered_rules": triggered_rules,
        "required_actions": required_actions,
        "compliant": len(triggered_rules) == 0,
    }

    return json.dumps(result, indent=2)


COMPLIANCE_TOOLS = [search_sanctions_list, get_client_transaction_history, check_regulatory_thresholds]
