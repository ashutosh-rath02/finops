"""Deterministic mock 6-month bank statement generator.

Seeded by PAN so results are reproducible across runs.
"""
from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta
from typing import Any, Dict, List


def get_bank_statement(pan: str, monthly_net_salary: float = 0) -> Dict[str, Any]:
    seed = int(hashlib.md5(f"bank_{pan}".encode()).hexdigest(), 16) % 100_000
    rng = random.Random(seed)

    today = date.today()
    months: List[Dict[str, Any]] = []

    running_balance = rng.uniform(50_000, 300_000)

    for m in range(5, -1, -1):
        month_start = date(today.year, today.month, 1) - timedelta(days=30 * m)
        month_label = month_start.strftime("%Y-%m")

        # Salary credit (may vary ±5%)
        salary_variance = rng.uniform(0.95, 1.05)
        salary_credit = round(monthly_net_salary * salary_variance, 2) if monthly_net_salary else rng.uniform(80_000, 150_000)

        # Debits: EMIs + living expenses + discretionary
        emi_debits = rng.uniform(15_000, 40_000)
        living_debits = rng.uniform(20_000, 60_000)
        discretionary = rng.uniform(5_000, 25_000)
        total_debits = emi_debits + living_debits + discretionary

        # Occasional large debits (investments, travel)
        if rng.random() < 0.3:
            total_debits += rng.uniform(20_000, 80_000)

        closing_balance = running_balance + salary_credit - total_debits
        closing_balance = max(closing_balance, 1_000)  # never negative in mock

        months.append({
            "month": month_label,
            "opening_balance": round(running_balance, 2),
            "total_credits": round(salary_credit + rng.uniform(0, 10_000), 2),
            "salary_credit": round(salary_credit, 2),
            "total_debits": round(total_debits, 2),
            "emi_debits": round(emi_debits, 2),
            "closing_balance": round(closing_balance, 2),
            "min_balance": round(closing_balance * rng.uniform(0.3, 0.8), 2),
            "bounce_count": rng.choices([0, 1, 2], weights=[85, 10, 5])[0],
        })
        running_balance = closing_balance

    avg_monthly_credit = sum(m["total_credits"] for m in months) / len(months)
    avg_closing_balance = sum(m["closing_balance"] for m in months) / len(months)
    total_bounces = sum(m["bounce_count"] for m in months)

    return {
        "pan": pan,
        "statement_period_months": 6,
        "account_type": rng.choice(["SAVINGS", "CURRENT"]),
        "bank": rng.choice(["HDFC Bank", "ICICI Bank", "SBI", "Axis Bank", "Kotak Mahindra"]),
        "avg_monthly_credit_inr": round(avg_monthly_credit, 2),
        "avg_closing_balance_inr": round(avg_closing_balance, 2),
        "total_cheque_bounces_6m": total_bounces,
        "salary_regularity": "REGULAR" if all(m["salary_credit"] > 0 for m in months) else "IRREGULAR",
        "monthly_statements": months,
    }
