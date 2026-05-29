"""Agent configuration objects.

Each AgentConfig holds the model, system prompt, and any runtime settings
for one stage of the pipeline. The actual API call is done in main.py.
"""
from __future__ import annotations

from dataclasses import dataclass

from agents.prompts import (
    BANK_ENRICHMENT_PROMPT,
    BUREAU_ENRICHMENT_PROMPT,
    COMPLIANCE_AGENT_PROMPT,
    DECISION_AGENT_PROMPT,
    GST_ENRICHMENT_PROMPT,
    INTAKE_AGENT_PROMPT,
    RISK_AGENT_PROMPT,
)


@dataclass
class AgentConfig:
    name: str
    system_prompt: str
    model: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.0  # deterministic for underwriting


INTAKE_AGENT = AgentConfig(
    name="intake-agent",
    system_prompt=INTAKE_AGENT_PROMPT,
)

BUREAU_ENRICHMENT_AGENT = AgentConfig(
    name="bureau-enrichment-agent",
    system_prompt=BUREAU_ENRICHMENT_PROMPT,
)

BANK_ENRICHMENT_AGENT = AgentConfig(
    name="bank-enrichment-agent",
    system_prompt=BANK_ENRICHMENT_PROMPT,
)

GST_ENRICHMENT_AGENT = AgentConfig(
    name="gst-enrichment-agent",
    system_prompt=GST_ENRICHMENT_PROMPT,
)

RISK_AGENT = AgentConfig(
    name="risk-agent",
    system_prompt=RISK_AGENT_PROMPT,
    max_tokens=8192,
)

COMPLIANCE_AGENT = AgentConfig(
    name="compliance-agent",
    system_prompt=COMPLIANCE_AGENT_PROMPT,
)

DECISION_AGENT = AgentConfig(
    name="decision-agent",
    system_prompt=DECISION_AGENT_PROMPT,
    max_tokens=8192,
)
