"""Full pipeline integration test.

Runs the complete underwriting pipeline on the sample application and
validates the output credit memo against the Pydantic schema.

Usage:
    python tests/test_pipeline.py
    # or
    pytest tests/test_pipeline.py -v -s
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path when run directly
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import underwrite
from models.credit_memo import CreditMemo, Recommendation


SAMPLE_APP = ROOT / "data" / "sample_application.json"
OUTPUT_DIR = Path("/tmp/underwriting/APP-2026-00142")


def test_pipeline_runs_end_to_end():
    memo: CreditMemo = asyncio.run(underwrite(SAMPLE_APP))

    # Recommendation must be one of the three valid values
    assert memo.recommendation in (
        Recommendation.APPROVE,
        Recommendation.REJECT,
        Recommendation.MANUAL_REVIEW,
    ), f"Unexpected recommendation: {memo.recommendation}"

    # Risk score in valid range
    assert 0 <= memo.risk_score <= 1000, f"Risk score out of range: {memo.risk_score}"

    # Audit trail: 7 entries — intake, bureau, bank, gst, risk, compliance, decision
    assert len(memo.audit_trail) == 7, (
        f"Expected 7 audit entries, got {len(memo.audit_trail)}. "
        f"Agents: {[e.agent for e in memo.audit_trail]}"
    )

    actual_agents = {e.agent for e in memo.audit_trail}
    # Verify every stage is represented
    for expected in ("intake-agent", "bureau-enrichment-agent", "bank-enrichment-agent",
                     "gst-enrichment-agent", "risk-agent", "compliance-agent", "decision-agent"):
        assert expected in actual_agents, f"Missing audit entry for {expected}"

    # Decision rationale must be non-empty
    assert memo.decision_rationale and len(memo.decision_rationale) > 50, (
        "decision_rationale is too short or empty"
    )

    # Flag list must be present (may be empty for clean applications)
    assert isinstance(memo.flag_summary, list)

    # Approved amount sanity check
    if memo.recommendation == Recommendation.APPROVE:
        assert memo.approved_amount is not None
        assert memo.approved_amount <= 1_500_000  # must not exceed requested

    # credit_memo.json must exist on disk
    memo_path = OUTPUT_DIR / "credit_memo.json"
    assert memo_path.exists(), f"credit_memo.json not found at {memo_path}"

    with open(memo_path, encoding="utf-8") as f:
        raw = json.load(f)
    assert raw["application_id"] == "APP-2026-00142"

    print("\n" + "=" * 60)
    print("  PIPELINE TEST PASSED")
    print(f"  Recommendation : {memo.recommendation}")
    print(f"  Risk Score     : {memo.risk_score} / 1000")
    print(f"  Flags          : {len(memo.flag_summary)}")
    print(f"  Audit entries  : {len(memo.audit_trail)}")
    print("=" * 60)
    print("\ncredit_memo.json contents:\n")
    print(json.dumps(raw, indent=2, default=str))

    return memo


if __name__ == "__main__":
    test_pipeline_runs_end_to_end()
