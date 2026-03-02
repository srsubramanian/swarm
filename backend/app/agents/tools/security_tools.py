"""Security domain tools — IP reputation, geo-velocity, device fingerprints.

All tools return simulated mock data keyed on the 4 built-in scenarios.
Interfaces are designed for easy swap to real implementations later.
"""

import json

from langchain_core.tools import tool


@tool
def lookup_ip_reputation(ip_address: str) -> str:
    """Look up threat intelligence and reputation data for an IP address.

    Args:
        ip_address: IPv4 address to look up.

    Returns:
        JSON string with threat score, ISP info, VPN/proxy/Tor detection,
        and abuse history.
    """
    reputations = {
        "185.220.101.42": {
            "threat_score": 78,
            "threat_level": "high",
            "isp": "Tor Exit Node Operator",
            "organization": "Tor Project",
            "is_tor": True,
            "is_vpn": False,
            "is_proxy": False,
            "is_datacenter": True,
            "country": "DE",
            "city": "Frankfurt",
            "abuse_reports_30d": 142,
            "last_seen_malicious": "2026-02-28T14:22:00Z",
            "notes": "Known Tor exit node. Frequently used in credential stuffing and scraping attacks.",
        },
        "91.108.56.130": {
            "threat_score": 35,
            "threat_level": "moderate",
            "isp": "Turk Telekom",
            "organization": "Turk Telekom Residential",
            "is_tor": False,
            "is_vpn": False,
            "is_proxy": False,
            "is_datacenter": False,
            "country": "TR",
            "city": "Istanbul",
            "abuse_reports_30d": 0,
            "last_seen_malicious": None,
            "notes": "Residential ISP in Istanbul. No known abuse history but geographically anomalous for this client.",
        },
        "203.0.113.50": {
            "threat_score": 5,
            "threat_level": "low",
            "isp": "Comcast Business",
            "organization": "Atlas Capital LLC",
            "is_tor": False,
            "is_vpn": False,
            "is_proxy": False,
            "is_datacenter": False,
            "country": "US",
            "city": "New York",
            "abuse_reports_30d": 0,
            "last_seen_malicious": None,
            "notes": "Known business IP for Atlas Capital NYC office.",
        },
    }

    result = reputations.get(
        ip_address,
        {
            "threat_score": 10,
            "threat_level": "low",
            "isp": "Unknown ISP",
            "organization": "Unknown",
            "is_tor": False,
            "is_vpn": False,
            "is_proxy": False,
            "is_datacenter": False,
            "country": "US",
            "city": "Unknown",
            "abuse_reports_30d": 0,
            "last_seen_malicious": None,
            "notes": f"No specific threat data for IP {ip_address}.",
        },
    )

    result["ip_address"] = ip_address
    return json.dumps(result, indent=2)


@tool
def check_geo_velocity(client_name: str, current_location: str) -> str:
    """Check for impossible travel or suspicious geo-velocity anomalies.

    Args:
        client_name: Name of the client to check.
        current_location: Current city/location string (e.g. 'Istanbul, Turkey').

    Returns:
        JSON string with travel analysis, distance, time gap, and
        impossible travel determination.
    """
    profiles = {
        "Atlas Capital": {
            "last_known_location": "New York, NY",
            "last_login_time": "2026-02-28T21:00:00Z",
            "typical_locations": ["New York, NY"],
            "travel_policy": "No international travel on file",
        },
        "Meridian Holdings": {
            "last_known_location": "London, UK",
            "last_login_time": "2026-02-28T09:00:00Z",
            "typical_locations": ["London, UK", "Nicosia, Cyprus", "Frankfurt, Germany"],
            "travel_policy": "Frequent EU travel for trade finance",
        },
        "Quantum Dynamics": {
            "last_known_location": "San Francisco, CA",
            "last_login_time": "2026-02-28T17:00:00Z",
            "typical_locations": ["San Francisco, CA"],
            "travel_policy": "Operations team works from SF office",
        },
        "Riverside Deli LLC": {
            "last_known_location": "Portland, OR",
            "last_login_time": "2026-02-28T16:00:00Z",
            "typical_locations": ["Portland, OR"],
            "travel_policy": "Local business, no travel expected",
        },
    }

    profile = profiles.get(client_name)
    if not profile:
        return json.dumps({
            "client_name": client_name,
            "current_location": current_location,
            "analysis": "unknown_client",
            "notes": f"No geo-velocity profile for client '{client_name}'.",
        }, indent=2)

    # Determine if current location is anomalous
    is_typical = current_location in profile["typical_locations"]
    last_loc = profile["last_known_location"]

    # Distance/travel calculations (mock)
    distance_data = {
        ("New York, NY", "Istanbul, Turkey"): {"miles": 5_013, "min_flight_hours": 10.5},
        ("New York, NY", "London, UK"): {"miles": 3_459, "min_flight_hours": 7.0},
        ("San Francisco, CA", "New York, NY"): {"miles": 2_586, "min_flight_hours": 5.5},
    }

    key = (last_loc, current_location)
    travel_info = distance_data.get(key, {"miles": 0, "min_flight_hours": 0})

    # Calculate time since last login
    from datetime import datetime, timezone

    last_login = datetime.fromisoformat(profile["last_login_time"])
    now = datetime(2026, 3, 1, 3, 42, 0, tzinfo=timezone.utc)  # Fixed for deterministic output
    hours_elapsed = (now - last_login).total_seconds() / 3600

    impossible_travel = (
        travel_info["miles"] > 0
        and hours_elapsed < travel_info["min_flight_hours"]
    )

    result = {
        "client_name": client_name,
        "current_location": current_location,
        "last_known_location": last_loc,
        "last_login_time": profile["last_login_time"],
        "hours_since_last_login": round(hours_elapsed, 1),
        "distance_miles": travel_info["miles"],
        "min_flight_hours": travel_info["min_flight_hours"],
        "is_typical_location": is_typical,
        "impossible_travel": impossible_travel,
        "risk_assessment": "high" if impossible_travel else ("medium" if not is_typical else "low"),
        "travel_policy": profile["travel_policy"],
    }

    return json.dumps(result, indent=2)


@tool
def get_device_fingerprint_history(client_name: str) -> str:
    """Retrieve device fingerprint history and trust status for a client.

    Args:
        client_name: Name of the client to look up.

    Returns:
        JSON string with known devices, new device detection, and
        risk indicators.
    """
    device_histories = {
        "Atlas Capital": {
            "known_devices": [
                {
                    "fingerprint": "a1b2c3d4-known",
                    "device_type": "desktop",
                    "os": "Windows 11",
                    "browser": "Chrome 122",
                    "first_seen": "2024-06-15",
                    "last_seen": "2026-02-28",
                    "trust_level": "verified",
                    "location": "New York, NY",
                },
            ],
            "new_devices": [
                {
                    "fingerprint": "d4e5f6a7-new",
                    "device_type": "mobile",
                    "os": "iOS 18",
                    "browser": "Safari Mobile",
                    "first_seen": "2026-03-01",
                    "trust_level": "unverified",
                    "location": "Istanbul, Turkey",
                },
            ],
            "risk_indicators": [
                "New unverified mobile device from atypical location",
                "Previous device was desktop-only — mobile access is new pattern",
                "Device fingerprint not in any known device registry",
            ],
            "recommendation": "Require step-up authentication before granting access",
        },
        "Meridian Holdings": {
            "known_devices": [
                {
                    "fingerprint": "b2c3d4e5-known",
                    "device_type": "desktop",
                    "os": "macOS 15",
                    "browser": "Safari 18",
                    "first_seen": "2023-01-10",
                    "last_seen": "2026-02-28",
                    "trust_level": "verified",
                    "location": "London, UK",
                },
            ],
            "new_devices": [],
            "risk_indicators": [],
            "recommendation": "No device anomalies detected",
        },
        "Quantum Dynamics": {
            "known_devices": [
                {
                    "fingerprint": "c3d4e5f6-known",
                    "device_type": "server",
                    "os": "Linux (API Client)",
                    "browser": "SDK v3.0",
                    "first_seen": "2024-03-01",
                    "last_seen": "2026-02-28",
                    "trust_level": "verified",
                    "location": "San Francisco, CA",
                },
            ],
            "new_devices": [],
            "risk_indicators": [],
            "recommendation": "No device anomalies detected",
        },
        "Riverside Deli LLC": {
            "known_devices": [
                {
                    "fingerprint": "e5f6a7b8-known",
                    "device_type": "desktop",
                    "os": "Windows 10",
                    "browser": "Chrome 121",
                    "first_seen": "2024-09-01",
                    "last_seen": "2026-02-28",
                    "trust_level": "verified",
                    "location": "Portland, OR",
                },
            ],
            "new_devices": [],
            "risk_indicators": [],
            "recommendation": "No device anomalies detected",
        },
    }

    result = device_histories.get(
        client_name,
        {
            "known_devices": [],
            "new_devices": [],
            "risk_indicators": [f"No device history for client '{client_name}'"],
            "recommendation": "Treat all devices as unverified",
        },
    )

    result["client_name"] = client_name
    result["total_known_devices"] = len(result["known_devices"])
    result["total_new_devices"] = len(result["new_devices"])
    return json.dumps(result, indent=2)


SECURITY_TOOLS = [lookup_ip_reputation, check_geo_velocity, get_device_fingerprint_history]
