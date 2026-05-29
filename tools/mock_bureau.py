"""Deterministic mock credit bureau report generator.

Seeded by PAN so the same applicant always gets the same report.
"""
from __future__ import annotations

import hashlib
import random
from datetime import date
from typing import Any, Dict, List


def get_bureau_report(pan: str) -> Dict[str, Any]:
    seed = int(hashlib.md5(pan.encode()).hexdigest(), 16) % 100_000
    rng = random.Random(seed)

    credit_score = rng.randint(620, 820)
    lenders = ["HDFC Bank", "ICICI Bank", "SBI", "Axis Bank", "Kotak Mahindra", "Yes Bank"]
    account_types = ["credit_card", "personal_loan", "home_loan", "auto_loan", "consumer_loan"]

    num_accounts = rng.randint(2, 7)
    accounts: List[Dict[str, Any]] = []
    for i in range(num_accounts):
        outstanding = rng.randint(0, 600_000)
        dpd = rng.choices([0, 30, 60, 90], weights=[80, 10, 6, 4])[0]
        acc_type = rng.choice(account_types)
        accounts.append({
            "account_id": f"ACC{pan[-4:]}{i+1:02d}",
            "type": acc_type,
            "lender": rng.choice(lenders),
            "outstanding_amount": outstanding,
            "sanctioned_limit": outstanding + rng.randint(0, 200_000),
            "current_emi": rng.randint(2_000, 18_000) if outstanding > 0 else 0,
            "days_past_due": dpd,
            "opened_months_ago": rng.randint(3, 96),
            "status": "ACTIVE" if rng.random() > 0.2 else "CLOSED",
        })

    total_outstanding = sum(a["outstanding_amount"] for a in accounts if a["status"] == "ACTIVE")
    total_emi = sum(a["current_emi"] for a in accounts if a["status"] == "ACTIVE")
    dpd_30 = sum(1 for a in accounts if a["days_past_due"] >= 30)
    dpd_60 = sum(1 for a in accounts if a["days_past_due"] >= 60)
    dpd_90 = sum(1 for a in accounts if a["days_past_due"] >= 90)

    return {
        "pan": pan,
        "report_date": date.today().isoformat(),
        "credit_score": credit_score,
        "score_band": _score_band(credit_score),
        "total_accounts": num_accounts,
        "active_accounts": sum(1 for a in accounts if a["status"] == "ACTIVE"),
        "closed_accounts": sum(1 for a in accounts if a["status"] == "CLOSED"),
        "total_outstanding_inr": total_outstanding,
        "total_active_emi_inr": total_emi,
        "enquiries_last_6_months": rng.randint(0, 6),
        "dpd_summary": {
            "30_plus_count": dpd_30,
            "60_plus_count": dpd_60,
            "90_plus_count": dpd_90,
        },
        "credit_utilization_pct": rng.randint(15, 85),
        "accounts": accounts,
    }


def _score_band(score: int) -> str:
    if score >= 750:
        return "EXCELLENT"
    if score >= 700:
        return "GOOD"
    if score >= 650:
        return "FAIR"
    return "POOR"
