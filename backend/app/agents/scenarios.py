"""Pre-built scenario definitions for the mock event queue.

Each scenario is a complete AnalyzeRequest extracted from backend/requests.http.
"""

from app.schemas.events import AnalyzeRequest

SCENARIOS: dict[str, AnalyzeRequest] = {
    "wire_transfer": AnalyzeRequest(
        event_type="wire_transfer",
        title="$2.4M Wire to Cyprus",
        client_name="Meridian Holdings",
        event_data={
            "amount": 2_400_000,
            "currency": "USD",
            "destination_country": "CY",
            "destination_bank": "Bank of Cyprus",
            "reference": "INV-2024-0847",
            "originator_account": "MHLD-0042",
            "ip_address": "185.220.101.42",
            "sdk_version": "3.1.2",
        },
        client_memory="Known client since 2019. Regular EU transfers for trade finance. Typical monthly volume: $500K-$1.2M. Previous Cyprus transfers in 2023 were cleared after EDD.",
    ),
    "velocity_alert": AnalyzeRequest(
        event_type="velocity_alert",
        title="47 Transactions in 3 Minutes — Quantum Dynamics",
        client_name="Quantum Dynamics",
        event_data={
            "transaction_count": 47,
            "time_window_seconds": 180,
            "total_amount": 892_000,
            "currency": "USD",
            "transaction_type": "batch_ach",
        },
        client_memory="Payroll processor. Monthly batch of 40-60 ACH transactions is normal. Uses SDK v3.0.",
    ),
    "security_alert": AnalyzeRequest(
        event_type="security_alert",
        title="New Device Login — Atlas Capital",
        client_name="Atlas Capital",
        event_data={
            "alert_type": "new_device",
            "ip_address": "91.108.56.130",
            "geo_location": "Istanbul, Turkey",
            "device_fingerprint": "d4e5f6a7-new",
            "previous_device": "a1b2c3d4-known",
            "previous_geo": "New York, NY",
            "login_time_utc": "2026-03-01T03:42:00Z",
            "failed_attempts_24h": 3,
            "mfa_method": "sms",
            "sdk_version": "2.9.1",
        },
        client_memory="US-based hedge fund. All prior logins from NYC office (IP range 203.0.113.0/24). Business hours 8am-7pm ET. No travel history on file.",
    ),
    "cash_deposit": AnalyzeRequest(
        event_type="cash_deposit",
        title="$9,800 Cash Deposit — Third This Week",
        client_name="Riverside Deli LLC",
        event_data={
            "amount": 9_800,
            "currency": "USD",
            "branch": "Main St Branch #042",
            "teller_id": "T-1187",
            "deposits_this_week": [
                {"date": "2026-02-27", "amount": 9_500},
                {"date": "2026-02-28", "amount": 9_700},
                {"date": "2026-03-01", "amount": 9_800},
            ],
            "weekly_total": 29_000,
            "account_type": "business_checking",
        },
        client_memory="Small restaurant. Typical weekly cash deposits $3K-$5K. No prior compliance flags.",
    ),
}
