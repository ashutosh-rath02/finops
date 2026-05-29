"""Deterministic mock GST filing summary generator.

For salaried applicants this returns a minimal record (not GST-registered).
For self-employed / business applicants it returns turnover and filing history.
"""
from __future__ import annotations

import hashlib
import random
from datetime import date
from typing import Any, Dict


def get_gst_summary(pan: str, employment_type: str = "salaried") -> Dict[str, Any]:
    seed = int(hashlib.md5(f"gst_{pan}".encode()).hexdigest(), 16) % 100_000
    rng = random.Random(seed)

    if employment_type == "salaried":
        return {
            "pan": pan,
            "gst_registered": False,
            "note": "Salaried individual — GST registration not applicable.",
            "gstin": None,
            "annual_turnover_inr": None,
            "filing_compliance_pct": None,
            "returns_filed_12m": None,
            "returns_due_12m": None,
        }

    gstin = f"27{pan}1Z{rng.choice('ABCDEFGH')}"
    annual_turnover = rng.uniform(2_000_000, 30_000_000)
    returns_due = 24  # GSTR-1 + GSTR-3B monthly for 12 months
    returns_filed = rng.randint(18, 24)
    compliance_pct = round(returns_filed / returns_due * 100, 1)

    quarterly_breakdown = []
    quarters = ["Q1 FY25", "Q2 FY25", "Q3 FY25", "Q4 FY25"]
    for q in quarters:
        qtr_turnover = annual_turnover / 4 * rng.uniform(0.8, 1.2)
        quarterly_breakdown.append({
            "quarter": q,
            "turnover_inr": round(qtr_turnover, 2),
            "tax_paid_inr": round(qtr_turnover * 0.18, 2),
            "filed_on_time": rng.random() > 0.15,
        })

    return {
        "pan": pan,
        "gst_registered": True,
        "gstin": gstin,
        "registration_date": f"{rng.randint(2018, 2022)}-{rng.randint(1,12):02d}-01",
        "annual_turnover_inr": round(annual_turnover, 2),
        "returns_due_12m": returns_due,
        "returns_filed_12m": returns_filed,
        "filing_compliance_pct": compliance_pct,
        "quarterly_breakdown": quarterly_breakdown,
    }
