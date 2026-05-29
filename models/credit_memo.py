from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class Recommendation(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskFlag(BaseModel):
    flag_id: str
    category: str
    severity: Severity
    description: str
    source_agent: str
    evidence: str


class AuditEntry(BaseModel):
    timestamp: datetime
    agent: str
    action: str
    input_summary: str
    output_summary: str
    duration_ms: Optional[int] = None


class CreditMemo(BaseModel):
    application_id: str
    generated_at: datetime
    recommendation: Recommendation
    risk_score: int  # 0–1000; higher = riskier
    decision_rationale: str
    audit_trail: List[AuditEntry]
    flag_summary: List[RiskFlag]
    approved_amount: Optional[float] = None
    approved_tenure_months: Optional[int] = None
    conditions: Optional[List[str]] = None
