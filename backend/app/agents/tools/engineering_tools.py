"""Engineering domain tools — SDK versions, rate limits, metadata validation.

All tools return simulated mock data keyed on the 4 built-in scenarios.
Interfaces are designed for easy swap to real implementations later.
"""

import json

from langchain_core.tools import tool


@tool
def check_sdk_version_status(version: str) -> str:
    """Check the lifecycle status of a client SDK version.

    Args:
        version: SDK version string (e.g. '3.1.2', '3.0', '2.9.1').

    Returns:
        JSON string with version status, known CVEs, deprecation info,
        and upgrade recommendations.
    """
    versions = {
        "3.1.2": {
            "status": "current",
            "release_date": "2026-01-15",
            "end_of_support": None,
            "known_cves": [],
            "deprecation_notice": None,
            "latest_version": "3.1.2",
            "upgrade_urgency": "none",
            "notes": "Latest stable release. All security patches applied.",
        },
        "3.1.0": {
            "status": "supported",
            "release_date": "2025-10-01",
            "end_of_support": "2026-10-01",
            "known_cves": [],
            "deprecation_notice": None,
            "latest_version": "3.1.2",
            "upgrade_urgency": "low",
            "notes": "Supported but minor patch updates available.",
        },
        "3.0": {
            "status": "deprecated",
            "release_date": "2025-03-01",
            "end_of_support": "2026-03-01",
            "known_cves": [
                {
                    "id": "CVE-2025-4821",
                    "severity": "medium",
                    "description": "Timing side-channel in HMAC validation allows signature bypass under specific conditions.",
                    "fixed_in": "3.0.1",
                }
            ],
            "deprecation_notice": "SDK v3.0 reaches end-of-support on 2026-03-01. Upgrade to v3.1.x.",
            "latest_version": "3.1.2",
            "upgrade_urgency": "high",
            "notes": "Deprecated with known CVE. Clients should upgrade immediately.",
        },
        "2.9.1": {
            "status": "end_of_life",
            "release_date": "2024-06-15",
            "end_of_support": "2025-06-15",
            "known_cves": [
                {
                    "id": "CVE-2025-3192",
                    "severity": "high",
                    "description": "Insecure deserialization in request payload parsing allows remote code execution.",
                    "fixed_in": "3.0",
                },
                {
                    "id": "CVE-2025-4821",
                    "severity": "medium",
                    "description": "Timing side-channel in HMAC validation.",
                    "fixed_in": "3.0.1",
                },
            ],
            "deprecation_notice": "SDK v2.x is end-of-life. No further patches will be released.",
            "latest_version": "3.1.2",
            "upgrade_urgency": "critical",
            "notes": "End-of-life with 2 unpatched vulnerabilities including a critical RCE. Immediate upgrade required.",
        },
    }

    result = versions.get(
        version,
        {
            "status": "unknown",
            "release_date": None,
            "end_of_support": None,
            "known_cves": [],
            "deprecation_notice": None,
            "latest_version": "3.1.2",
            "upgrade_urgency": "unknown",
            "notes": f"SDK version '{version}' not found in version registry.",
        },
    )

    result["queried_version"] = version
    return json.dumps(result, indent=2)


@tool
def get_api_rate_limit_status(client_id: str) -> str:
    """Check current API rate limit consumption and burst detection for a client.

    Args:
        client_id: Client identifier or account name.

    Returns:
        JSON string with rate limit quotas, current usage, burst detection,
        and throttling status.
    """
    rate_limits = {
        "Quantum Dynamics": {
            "tier": "enterprise",
            "requests_per_minute": 500,
            "current_rpm": 47,
            "requests_per_hour": 10_000,
            "current_rph": 3_842,
            "burst_detected": True,
            "burst_details": {
                "window": "3 minutes",
                "request_count": 47,
                "avg_requests_per_minute": 15.7,
                "burst_ratio": 3.0,
                "classification": "within_limits_but_bursty",
            },
            "throttled": False,
            "notes": "Burst detected but within enterprise tier limits. Pattern consistent with batch processing.",
        },
        "Meridian Holdings": {
            "tier": "business",
            "requests_per_minute": 100,
            "current_rpm": 2,
            "requests_per_hour": 2_000,
            "current_rph": 12,
            "burst_detected": False,
            "burst_details": None,
            "throttled": False,
            "notes": "Normal API usage. Well within rate limits.",
        },
        "Atlas Capital": {
            "tier": "enterprise",
            "requests_per_minute": 500,
            "current_rpm": 8,
            "requests_per_hour": 10_000,
            "current_rph": 145,
            "burst_detected": False,
            "burst_details": None,
            "throttled": False,
            "notes": "Normal API usage from known endpoints.",
        },
        "Riverside Deli LLC": {
            "tier": "basic",
            "requests_per_minute": 30,
            "current_rpm": 1,
            "requests_per_hour": 500,
            "current_rph": 5,
            "burst_detected": False,
            "burst_details": None,
            "throttled": False,
            "notes": "Minimal API usage. Typical for branch-based deposits.",
        },
    }

    result = rate_limits.get(
        client_id,
        {
            "tier": "unknown",
            "requests_per_minute": 0,
            "current_rpm": 0,
            "requests_per_hour": 0,
            "current_rph": 0,
            "burst_detected": False,
            "burst_details": None,
            "throttled": False,
            "notes": f"No rate limit data for client '{client_id}'.",
        },
    )

    result["client_id"] = client_id
    return json.dumps(result, indent=2)


@tool
def validate_transaction_metadata(reference_id: str) -> str:
    """Validate a transaction reference ID for format, duplicates, and correlation.

    Args:
        reference_id: Transaction reference identifier (e.g. 'INV-2024-0847').

    Returns:
        JSON string with format validation, duplicate check, and
        correlation chain analysis.
    """
    known_references = {
        "INV-2024-0847": {
            "format_valid": True,
            "format_pattern": "INV-YYYY-NNNN",
            "is_duplicate": False,
            "duplicate_count": 0,
            "correlation_chain": [
                {"step": "invoice_created", "timestamp": "2026-02-25T10:00:00Z", "system": "ERP"},
                {"step": "payment_initiated", "timestamp": "2026-03-01T09:30:00Z", "system": "Treasury"},
                {"step": "wire_submitted", "timestamp": "2026-03-01T09:35:00Z", "system": "SWIFT"},
            ],
            "metadata_consistency": "valid",
            "notes": "Reference ID follows expected format. Complete correlation chain from invoice to wire.",
        },
        "BATCH-20260301-QD": {
            "format_valid": True,
            "format_pattern": "BATCH-YYYYMMDD-XX",
            "is_duplicate": False,
            "duplicate_count": 0,
            "correlation_chain": [
                {"step": "batch_created", "timestamp": "2026-03-01T14:00:00Z", "system": "Payroll"},
                {"step": "ach_submitted", "timestamp": "2026-03-01T14:05:00Z", "system": "ACH Gateway"},
            ],
            "metadata_consistency": "valid",
            "notes": "Batch reference follows expected pattern for payroll processor.",
        },
    }

    # Check format validity for unknown references
    import re

    known_patterns = [
        (r"^INV-\d{4}-\d{4}$", "INV-YYYY-NNNN"),
        (r"^BATCH-\d{8}-[A-Z]{2}$", "BATCH-YYYYMMDD-XX"),
        (r"^TXN-[A-F0-9]{8}$", "TXN-XXXXXXXX"),
    ]

    result = known_references.get(reference_id)
    if result is None:
        format_valid = False
        matched_pattern = None
        for pattern, name in known_patterns:
            if re.match(pattern, reference_id):
                format_valid = True
                matched_pattern = name
                break

        result = {
            "format_valid": format_valid,
            "format_pattern": matched_pattern or "unknown",
            "is_duplicate": False,
            "duplicate_count": 0,
            "correlation_chain": [],
            "metadata_consistency": "incomplete" if format_valid else "invalid_format",
            "notes": f"Reference '{reference_id}' — {'valid format but no correlation data' if format_valid else 'does not match any known format pattern'}.",
        }

    result["reference_id"] = reference_id
    return json.dumps(result, indent=2)


ENGINEERING_TOOLS = [check_sdk_version_status, get_api_rate_limit_status, validate_transaction_metadata]
