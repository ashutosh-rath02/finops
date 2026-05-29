# Credit Underwriting Engine

## Project Goal
Autonomous multi-agent system that underwrites loan applications end-to-end
using the Claude Agent SDK. Produces a structured credit memo with full audit trail.

## Architecture
Orchestrator (main.py) spawns 5 subagents in a pipeline:
1. **intake-agent** — validates and normalizes raw application JSON
2. **enrichment-agent** — runs bureau, employment, bank, GST checks IN PARALLEL
3. **risk-agent** — scores the application, flags anomalies
4. **compliance-agent** — checks regulatory rules, builds audit trail
5. **decision-agent** — synthesizes everything into a final credit memo

## Key Rules
- Enrichment sub-tasks must run in parallel (use asyncio.gather)
- Every field in the credit memo must cite its source evidence
- Compliance check is NEVER skippable — gate the decision agent behind it
- All agent outputs write to /tmp/underwriting/{application_id}/ as JSON files
- Subagents must not spawn their own subagents

## Tech Stack
- Anthropic Python SDK (anthropic package)
- Pydantic v2 for all data models
- No external APIs — use mock data generators for bureau/bank data
- Python 3.11+
- asyncio for parallel enrichment

## Output
Final output is a credit_memo.json with:
- recommendation: APPROVE | REJECT | MANUAL_REVIEW
- risk_score: 0–1000
- decision_rationale: string with evidence citations
- audit_trail: list of every agent action with timestamps
- flag_summary: list of risk flags raised
