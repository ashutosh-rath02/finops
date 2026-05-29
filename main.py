"""Credit Underwriting Engine — Orchestrator.

Pipeline:
  intake-agent
    → enrichment (bureau + bank + GST run IN PARALLEL)
    → risk-agent
    → compliance-agent   ← gates the decision
    → decision-agent
    → credit_memo.json
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from openai import AsyncOpenAI

from agents.definitions import (
    BANK_ENRICHMENT_AGENT,
    BUREAU_ENRICHMENT_AGENT,
    COMPLIANCE_AGENT,
    DECISION_AGENT,
    GST_ENRICHMENT_AGENT,
    INTAKE_AGENT,
    RISK_AGENT,
    AgentConfig,
)
from models.application import LoanApplication
from models.credit_memo import AuditEntry, CreditMemo, RiskFlag
from tools.mock_bank import get_bank_statement
from tools.mock_bureau import get_bureau_report
from tools.mock_gst import get_gst_summary


def _require_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise EnvironmentError(
            "OPENAI_API_KEY is not set. Export it before running: "
            "export OPENAI_API_KEY=sk-..."
        )
    return key


def _output_dir(application_id: str) -> Path:
    d = Path("/tmp/underwriting") / application_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _save(application_id: str, filename: str, data: Any) -> None:
    path = _output_dir(application_id) / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _build_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=_require_api_key())


async def _call_agent(
    client: AsyncOpenAI,
    agent: AgentConfig,
    user_message: str,
) -> Dict[str, Any]:
    """Call the model with the agent's system prompt; return parsed JSON."""
    response = await client.chat.completions.create(
        model=agent.model,
        max_tokens=agent.max_tokens,
        temperature=agent.temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": agent.system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    return json.loads(raw)


# ─── Pipeline stages ──────────────────────────────────────────────────────────

async def run_intake(
    client: AsyncOpenAI,
    app: LoanApplication,
    audit: list,
) -> Dict[str, Any]:
    print("[intake-agent] Validating application…")
    t0 = time.monotonic()
    user_msg = f"Validate and normalize this loan application:\n\n{app.model_dump_json(indent=2)}"
    result = await _call_agent(client, INTAKE_AGENT, user_msg)
    ms = int((time.monotonic() - t0) * 1000)
    audit.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "intake-agent",
        "action": "validate_and_normalize",
        "input_summary": f"application_id={app.application_id}",
        "output_summary": f"status={result.get('status')} flags={len(result.get('intake_flags', []))}",
        "duration_ms": ms,
    })
    return result


async def _run_bureau(client: AsyncOpenAI, app: LoanApplication) -> Dict[str, Any]:
    print("[bureau-enrichment-agent] Fetching bureau report…")
    t0 = time.monotonic()
    bureau_data = get_bureau_report(app.applicant.pan)
    user_msg = (
        f"Application:\n{app.model_dump_json(indent=2)}\n\n"
        f"Bureau report:\n{json.dumps(bureau_data, indent=2)}"
    )
    result = await _call_agent(client, BUREAU_ENRICHMENT_AGENT, user_msg)
    result["_duration_ms"] = int((time.monotonic() - t0) * 1000)
    return result


async def _run_bank(client: AsyncOpenAI, app: LoanApplication) -> Dict[str, Any]:
    print("[bank-enrichment-agent] Analysing bank statement…")
    t0 = time.monotonic()
    bank_data = get_bank_statement(app.applicant.pan, app.employment.monthly_net_salary or 0)
    user_msg = (
        f"Application:\n{app.model_dump_json(indent=2)}\n\n"
        f"Bank statement (6 months):\n{json.dumps(bank_data, indent=2)}"
    )
    result = await _call_agent(client, BANK_ENRICHMENT_AGENT, user_msg)
    result["_duration_ms"] = int((time.monotonic() - t0) * 1000)
    return result


async def _run_gst(client: AsyncOpenAI, app: LoanApplication) -> Dict[str, Any]:
    print("[gst-enrichment-agent] Checking GST records…")
    t0 = time.monotonic()
    gst_data = get_gst_summary(app.applicant.pan, app.employment.type.value)
    user_msg = (
        f"Application:\n{app.model_dump_json(indent=2)}\n\n"
        f"GST summary:\n{json.dumps(gst_data, indent=2)}"
    )
    result = await _call_agent(client, GST_ENRICHMENT_AGENT, user_msg)
    result["_duration_ms"] = int((time.monotonic() - t0) * 1000)
    return result


async def run_enrichment(
    client: AsyncOpenAI,
    app: LoanApplication,
    audit: list,
) -> Dict[str, Any]:
    print("[enrichment] Running bureau + bank + GST in parallel…")
    bureau_result, bank_result, gst_result = await asyncio.gather(
        _run_bureau(client, app),
        _run_bank(client, app),
        _run_gst(client, app),
    )
    for name, res, flag_key in [
        ("bureau-enrichment-agent", bureau_result, "bureau_flags"),
        ("bank-enrichment-agent", bank_result, "bank_flags"),
        ("gst-enrichment-agent", gst_result, "gst_flags"),
    ]:
        audit.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": name,
            "action": "enrich",
            "input_summary": f"pan={app.applicant.pan}",
            "output_summary": f"flags={len(res.get(flag_key, []))}",
            "duration_ms": res.pop("_duration_ms", None),
        })
    return {"bureau": bureau_result, "bank": bank_result, "gst": gst_result}


async def run_risk(
    client: AsyncOpenAI,
    app: LoanApplication,
    intake: Dict[str, Any],
    enrichment: Dict[str, Any],
    audit: list,
) -> Dict[str, Any]:
    print("[risk-agent] Scoring risk…")
    t0 = time.monotonic()
    user_msg = (
        f"Application:\n{app.model_dump_json(indent=2)}\n\n"
        f"Intake analysis:\n{json.dumps(intake, indent=2)}\n\n"
        f"Bureau enrichment:\n{json.dumps(enrichment['bureau'], indent=2)}\n\n"
        f"Bank enrichment:\n{json.dumps(enrichment['bank'], indent=2)}\n\n"
        f"GST enrichment:\n{json.dumps(enrichment['gst'], indent=2)}"
    )
    result = await _call_agent(client, RISK_AGENT, user_msg)
    ms = int((time.monotonic() - t0) * 1000)
    audit.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "risk-agent",
        "action": "score_and_flag",
        "input_summary": f"application_id={app.application_id}",
        "output_summary": (
            f"risk_score={result.get('risk_score')} "
            f"recommendation={result.get('preliminary_recommendation')}"
        ),
        "duration_ms": ms,
    })
    return result


async def run_compliance(
    client: AsyncOpenAI,
    app: LoanApplication,
    intake: Dict[str, Any],
    risk: Dict[str, Any],
    audit: list,
) -> Dict[str, Any]:
    print("[compliance-agent] Running compliance checks…")
    t0 = time.monotonic()
    user_msg = (
        f"Application:\n{app.model_dump_json(indent=2)}\n\n"
        f"Intake analysis:\n{json.dumps(intake, indent=2)}\n\n"
        f"Risk assessment:\n{json.dumps(risk, indent=2)}"
    )
    result = await _call_agent(client, COMPLIANCE_AGENT, user_msg)
    ms = int((time.monotonic() - t0) * 1000)
    audit.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "compliance-agent",
        "action": "compliance_check",
        "input_summary": f"application_id={app.application_id}",
        "output_summary": (
            f"compliance_status={result.get('compliance_status')} "
            f"checks={len(result.get('compliance_checks', []))}"
        ),
        "duration_ms": ms,
    })
    return result


async def run_decision(
    client: AsyncOpenAI,
    app: LoanApplication,
    intake: Dict[str, Any],
    enrichment: Dict[str, Any],
    risk: Dict[str, Any],
    compliance: Dict[str, Any],
    audit: list,
) -> Dict[str, Any]:
    print("[decision-agent] Synthesising final credit memo…")
    t0 = time.monotonic()

    if compliance.get("compliance_status") == "FAILED":
        print("[decision-agent] WARNING: Compliance FAILED — recommendation must be REJECT.")

    user_msg = (
        f"Application:\n{app.model_dump_json(indent=2)}\n\n"
        f"Intake analysis:\n{json.dumps(intake, indent=2)}\n\n"
        f"Bureau enrichment:\n{json.dumps(enrichment['bureau'], indent=2)}\n\n"
        f"Bank enrichment:\n{json.dumps(enrichment['bank'], indent=2)}\n\n"
        f"GST enrichment:\n{json.dumps(enrichment['gst'], indent=2)}\n\n"
        f"Risk assessment:\n{json.dumps(risk, indent=2)}\n\n"
        f"Compliance check:\n{json.dumps(compliance, indent=2)}\n\n"
        f"Prior audit trail:\n{json.dumps(audit, indent=2)}"
    )
    result = await _call_agent(client, DECISION_AGENT, user_msg)
    ms = int((time.monotonic() - t0) * 1000)
    audit.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "decision-agent",
        "action": "synthesise_credit_memo",
        "input_summary": f"application_id={app.application_id}",
        "output_summary": (
            f"recommendation={result.get('recommendation')} "
            f"risk_score={result.get('risk_score')}"
        ),
        "duration_ms": ms,
    })
    return result


# ─── Main entry point ─────────────────────────────────────────────────────────

async def underwrite(application_path: str | Path) -> CreditMemo:
    client = _build_client()

    with open(application_path, encoding="utf-8") as f:
        raw = json.load(f)
    app = LoanApplication.model_validate(raw)
    app_id = app.application_id

    print(f"\n{'='*60}")
    print(f"  Credit Underwriting Engine")
    print(f"  Application: {app_id}")
    print(f"  Applicant:   {app.applicant.name}")
    print(f"  Loan:        ₹{app.product.amount_requested:,.0f} / {app.product.tenure_months}m")
    print(f"{'='*60}\n")

    audit: list = []

    # Stage 1: Intake
    intake = await run_intake(client, app, audit)
    _save(app_id, "01_intake.json", intake)

    if intake.get("status") == "INVALID":
        print(f"[FATAL] Application invalid: {intake.get('validation_errors')}")
        sys.exit(1)

    # Stage 2: Enrichment (parallel)
    enrichment = await run_enrichment(client, app, audit)
    _save(app_id, "02_enrichment_bureau.json", enrichment["bureau"])
    _save(app_id, "02_enrichment_bank.json", enrichment["bank"])
    _save(app_id, "02_enrichment_gst.json", enrichment["gst"])

    # Stage 3: Risk
    risk = await run_risk(client, app, intake, enrichment, audit)
    _save(app_id, "03_risk.json", risk)

    # Stage 4: Compliance (NEVER skipped)
    compliance = await run_compliance(client, app, intake, risk, audit)
    _save(app_id, "04_compliance.json", compliance)

    # Stage 5: Decision (gated on compliance)
    decision = await run_decision(client, app, intake, enrichment, risk, compliance, audit)

    # Our orchestrator's audit trail is authoritative
    decision["audit_trail"] = audit
    _save(app_id, "credit_memo.json", decision)

    memo = CreditMemo.model_validate(decision)

    out_path = _output_dir(app_id) / "credit_memo.json"
    print(f"\n{'='*60}")
    print(f"  RESULT       : {memo.recommendation}")
    print(f"  Risk Score   : {memo.risk_score} / 1000")
    print(f"  Flags        : {len(memo.flag_summary)}")
    print(f"  Credit memo  : {out_path}")
    print(f"{'='*60}\n")

    return memo


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_application.json"
    asyncio.run(underwrite(path))
