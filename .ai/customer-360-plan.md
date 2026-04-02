# Customer 360 Agent — Implementation Plan

> **Status: Complete** (2026-04-02). All 9 steps implemented, deployed as `customer360-assistant` v6. E2E test Run 8 achieved 6/6 validation (100%). Token optimizations: trimmed instructions (-44%), combined SN queries (-22% tool calls), 60min describe cache. See `.ai/e2e-results-history.md` for full optimization progression across 8 runs.

## Context

This project already deploys a Salesforce MCP server + chat-app + full Azure infrastructure (APIM, AI Foundry, Container Apps, App Insights). The `snow-meta-tool` project rides on the same infrastructure, adding a ServiceNow MCP server. Both have OBO identity propagation via APIM and Foundry connections (`salesforce-obo`, `servicenow-obo`) in the same Foundry project.

**Goal**: Add a Customer 360 agent that connects to **both** MCP tools, enabling cross-system CRM+ITSM queries. No new infrastructure needed — just a new agent definition + deployment automation + demo data.

## What Changes

### 1. Modify `hooks/postprovision.py`

Add three new functions following the existing patterns:

#### a) `create_customer360_agent()` (after `create_agent()` at line 552)
- Same pattern as `create_agent()` but with **two MCPTool instances**:
  - `salesforce_mcp` → `salesforce-obo` connection, 7 allowed tools (whoami, list_objects, describe_object, soql_query, search_records, write_record, process_approval)
  - `servicenow_mcp` → `servicenow-obo` connection, 3 allowed tools (discover, query, write)
- Derives SN endpoint from `APIM_GATEWAY_URL` + `/servicenow-mcp-obo/mcp`
- **Pre-check**: Verify `servicenow-obo` connection exists via ARM REST GET before proceeding. Skip gracefully with clear message if not found (SN project not deployed yet).
- Agent name: `customer360-assistant`
- Model: `gpt-5.4`
- Reuses existing `project-memory` store via `MemorySearchTool`
- System instructions combine SF + SN specifics with cross-system correlation guidance (see section 2)

#### b) `create_customer360_application()` (after `create_agent_application()` at line 756)
- Same pattern as `create_agent_application()`
- `app_name = "customer360-assistant"`, `agent_name = "customer360-assistant"`
- No Bot Service or Teams app needed — chat-app discovers it automatically via Foundry SDK

#### c) `create_customer360_deployment()` (after `create_agent_deployment()` at line 827)
- Same pattern as `create_agent_deployment()`
- `deployment_name = "customer360-assistant"`
- Includes traffic routing update

#### d) Update `main()` (at line 1193)
Add three new steps after Step 6 (before Bot Service at Step 7):
```
Step 6b: Create Customer 360 agent       → create_customer360_agent()
Step 6c: Customer 360 Agent Application  → create_customer360_application()
Step 6d: Customer 360 Agent Deployment   → create_customer360_deployment(version)
```
Each wrapped in try/except with non-fatal handling, same as existing steps.

### 2. Agent System Instructions

The Customer 360 agent instructions should include:

- **Mission**: Unified view of customers across CRM (Salesforce) and ITSM (ServiceNow)
- **Tool routing**: Which tool to use for what (SF for accounts/opps/cases, SN for incidents/problems/changes)
- **Cross-system workflow**: Plan → query SF first → query SN with matching company names → correlate → synthesize
- **Correlation patterns**: Match by company name (SF Account.Name ↔ SN company field), email domain, case/incident keywords, timing
- **Business insight patterns**: Revenue at risk, case-incident correlation, customer health, change risk
- **SF-specific rules**: Reuse from existing SF agent instructions in `create_agent()` (SOQL, error recovery, describe before write, whoami for "my" queries)
- **SN-specific rules**: Reuse from existing SN agent instructions in `snow-meta-tool/hooks/postprovision.py` (encoded query syntax, discover before write, fields parameter)
- **Memory**: Same per-user memory store (`project-memory`), no explicit save needed
- **Rules**: Confirm before writes in either system, explain correlation reasoning, present monetary amounts prominently

### 3. Demo Data

Create `docs/DEMO_DATA_SETUP.md` — adapt from `~/projects/snow-meta-tool/DEMO_DATA_SETUP.md` which already defines correlated data across both systems:
- **5 companies**: Acme Corp, Northwind Traders, Contoso Ltd, Fabrikam Inc, Adventure Works
- **Salesforce**: Accounts, Contacts (2 per account), Opportunities (mix of stages + amounts), Cases (correlated to SN incidents)
- **ServiceNow**: Incidents (P1-P4 tied to companies), Problems, Change Requests
- **Correlation**: Same company names, overlapping timelines, matching keywords between SF Cases and SN Incidents

### 4. Test Prompts

Create `docs/TEST_PROMPTS_360.md` with cross-system scenarios:

| Scenario | Example Prompt |
|----------|---------------|
| Unified lookup | "Give me a Customer 360 view for Contoso Ltd" |
| Revenue at risk | "We have a P1 incident about API gateway failures. Which SF accounts and open opportunities are affected?" |
| Meeting prep | "Prepare me for my QBR with Acme Corp — pull everything from both systems" |
| Change risk | "We're planning a billing upgrade Saturday. Check the SN change request and SF accounts with upcoming renewals" |
| Executive summary | "Cross-system report: total open P1 incidents, total pipeline value, and for each P1, identify impacted accounts with open deals" |
| Proactive outreach | "Acme Corp called about portal issues. Pull their full profile from both systems" |
| Case-incident correlation | "Show me all SF cases and SN incidents for Fabrikam from the last 30 days — are any related?" |

### 5. Documentation

Update `AGENT.md` to document the Customer 360 agent alongside the existing Salesforce assistant.

### 6. Demo Data Seeding Script

Create `scripts/seed_demo_data.py` — seeds **both** Salesforce and ServiceNow with correlated data for the Customer 360 demo.

**Reference files**:
- `~/projects/snow-meta-tool/scripts/seed_test_data.py` — SN seeding pattern (httpx + basic auth, REST API)
- `~/projects/snow-meta-tool/DEMO_DATA_SETUP.md` — complete correlated data specification
- `scripts/sf_utils.py` — SF CLI helpers (`get_access_token()`, `soql_query()`)

**Data to seed** (from DEMO_DATA_SETUP.md):

| System | Object | Count | Purpose |
|--------|--------|-------|---------|
| **Salesforce** | Accounts | 5 | Acme Corp, Northwind Traders, Contoso Ltd, Fabrikam Inc, Adventure Works |
| **Salesforce** | Contacts | 6 | 1-2 per account, matching email domains |
| **Salesforce** | Opportunities | 5 | Mix of stages + amounts ($180K-$1.2M) for revenue-at-risk scenarios |
| **Salesforce** | Cases | 6 | Open cases correlated to SN incidents by keywords |
| **ServiceNow** | Incidents | 6 | P1-P3, descriptions mention SF account names |
| **ServiceNow** | Problems | 1 | Root cause linking multiple incidents |
| **ServiceNow** | Change Requests | 2 | For change risk assessment scenarios |

**Architecture**:
```python
# Salesforce: use SF REST API via access token from sf CLI
sf_token, sf_instance = get_access_token(sf_org)  # from sf_utils.py
sf_client = httpx.Client(base_url=sf_instance, headers={"Authorization": f"Bearer {sf_token}"})

# ServiceNow: use REST API with basic auth (same as existing seed_test_data.py)
sn_client = httpx.Client(base_url=sn_instance, auth=(admin_user, admin_password))
```

**Key design**:
- Idempotent: check if records exist before creating (query by Name/short_description)
- Print created record IDs/numbers for verification
- `--sf-org` flag for SF CLI org alias, `--sn-instance` + `--sn-admin-password` for SN
- Optional `--cleanup` flag to delete seeded records

### 7. E2E Test Script

Create `scripts/test_e2e_customer360.py` — full progressive demo test covering all 6 use cases via Foundry Responses API.

**Reference file**: `~/projects/snow-meta-tool/scripts/test_e2e_tokens.py` — Responses API test harness with OAuth consent, MCP approval auto-approve, multi-turn conversation, token tracking.

**Reuse from existing test** (copy helper functions):
- `load_azd_env()` — loads azd environment variables
- `dump_output_items()` — prints output items summary
- `print_usage()` — prints token usage per turn
- `handle_approval()` — auto-approves MCP tool calls (recursive)

**Test scenarios — progressive demo story** (multi-turn conversation):
```python
scenarios = [
    # --- Level 1: Unified Lookup ---
    {
        "label": "1. Unified lookup",
        "query": "Tell me everything about Contoso Ltd",
        "expect_tools": ["salesforce_mcp", "servicenow_mcp"],
        "demonstrates": "Multi-tool orchestration, data correlation",
    },
    # --- Level 2: Cross-system Correlation ---
    {
        "label": "2. Cross-system correlation",
        "query": "Acme Corp reports API gateway outages — what's the full picture? "
                 "Check both their Salesforce cases and ServiceNow incidents.",
        "expect_tools": ["salesforce_mcp", "servicenow_mcp"],
        "demonstrates": "SF Cases ↔ SNOW Incidents correlation",
    },
    # --- Level 3: Meeting Prep ---
    {
        "label": "3. Meeting prep",
        "query": "Prepare me for my call with Fabrikam Inc tomorrow. "
                 "Pull their account details, any open opportunities, and active incidents.",
        "expect_tools": ["salesforce_mcp", "servicenow_mcp"],
        "demonstrates": "Account summary + open opps + active incidents",
    },
    # --- Level 4: Proactive Insights ---
    {
        "label": "4. Proactive insights",
        "query": "Which of our strategic accounts (by revenue) have the most "
                 "open incidents in ServiceNow? Show revenue at risk.",
        "expect_tools": ["salesforce_mcp", "servicenow_mcp"],
        "demonstrates": "Cross-system analytics, prioritization",
    },
    # --- Level 5: Cross-system Actions ---
    {
        "label": "5. Cross-system actions (read-only verification)",
        "query": "Find the most critical open ServiceNow incident and tell me "
                 "which Salesforce case it correlates with. What would a new SF case "
                 "look like if I wanted to escalate this?",
        "expect_tools": ["salesforce_mcp", "servicenow_mcp"],
        "demonstrates": "Write operations across both systems (describe only, no actual write in test)",
    },
    # --- Level 6: Escalation Workflow ---
    {
        "label": "6. Escalation workflow",
        "query": "Show me all P1 and P2 incidents from ServiceNow, then for each one "
                 "identify which Salesforce accounts are affected and their total "
                 "pipeline value. Rank by revenue at risk.",
        "expect_tools": ["salesforce_mcp", "servicenow_mcp"],
        "demonstrates": "Multi-system read + action orchestration",
    },
]
```

**Validation logic** (per turn):
```python
# Check which MCP servers were called
mcp_calls = [item for item in output_items if getattr(item, "type", "") == "mcp_call"]
servers_called = set(getattr(call, "server_label", "") for call in mcp_calls)
expected = set(scenario.get("expect_tools", []))
if expected and not expected.issubset(servers_called):
    missing = expected - servers_called
    print(f"  WARN: Expected tools from {missing} but only got {servers_called}")
else:
    print(f"  OK: Called tools from {servers_called}")
```

**Summary output** (end of test):
```
  Turn  Input   Output   Total   Cached  Servers Called  Label
  ----  ------  ------  ------  ------  ---------------  -----
  1      3,200   1,100   4,300       0  SF+SN            Unified lookup
  2      5,400   1,300   6,700   2,100  SF+SN            Cross-system correlation
  ...
  TOTAL  28,000  7,200  35,200

  Cross-system validation: 6/6 turns called expected tools ✓
```

## Files Modified

| File | Action |
|------|--------|
| `hooks/postprovision.py` | Add 3 functions + update `main()` |
| `AGENT.md` | Add Customer 360 agent section |
| `scripts/seed_demo_data.py` | **New** — Seed SF (via SF CLI) + SN (via REST API) with correlated demo data |
| `scripts/test_e2e_customer360.py` | **New** — Progressive E2E test (6 demo scenarios) via Foundry Responses API |
| `docs/DEMO_DATA_SETUP.md` | **New** — Correlated demo data guide (adapted from snow-meta-tool) |
| `docs/TEST_PROMPTS_360.md` | **New** — Cross-system test prompts for manual testing |

## What Does NOT Change

- `src/` — no app code changes (chat-app already discovers all agents dynamically)
- `infra/` — no Bicep changes (both OBO connections already exist in Foundry)
- `src/salesforce-mcp/` — SF MCP server unchanged
- `~/projects/snow-meta-tool/` — separate project, untouched

## Prerequisites

- `snow-meta-tool` must be deployed first (`azd up`) so the `servicenow-obo` connection exists in Foundry
- Both MCP servers must be running (SF + SN Container Apps)

## Implementation Sequence

1. Add `create_customer360_agent()` function with dual MCPTool + system instructions
2. Add `create_customer360_application()` function
3. Add `create_customer360_deployment()` function
4. Update `main()` with Steps 6b/6c/6d
5. Create `scripts/seed_demo_data.py` (SF via sf_utils + SN via httpx REST)
6. Create `scripts/test_e2e_customer360.py` (based on `~/projects/snow-meta-tool/scripts/test_e2e_tokens.py`)
7. Create `docs/DEMO_DATA_SETUP.md` (adapt from `~/projects/snow-meta-tool/DEMO_DATA_SETUP.md`)
8. Create `docs/TEST_PROMPTS_360.md`
9. Update `AGENT.md`

## Verification

1. **Deploy agent**: Run `python hooks/postprovision.py` (or `azd up`)
2. **Seed demo data**: Run `python scripts/seed_demo_data.py --sf-org <alias> --sn-instance <url> --sn-admin-password <pw>`
   - Seeds 5 SF accounts, 6 contacts, 5 opportunities, 6 cases
   - Seeds 6 SN incidents, 1 problem, 2 change requests
   - Correlated by company name, keywords, and timing
3. **Run E2E test**: Run `python scripts/test_e2e_customer360.py`
   - Covers all 6 progressive demo scenarios (unified lookup → escalation workflow)
   - Validates both `salesforce_mcp` and `servicenow_mcp` tools are called per turn
   - Auto-approves MCP tool calls, handles OAuth consent
   - Reports token usage per turn and cross-system validation summary
4. **Manual test**: Open chat-app → select `customer360-assistant` → run prompts from `docs/TEST_PROMPTS_360.md`
5. **Observability**: Check App Insights for OBO token exchanges to both Salesforce and ServiceNow

## Key Reference Files

- `hooks/postprovision.py` — primary file to modify (existing patterns at lines 552, 756, 827, 1193)
- `scripts/sf_utils.py` — SF CLI helpers: `get_access_token()`, `soql_query()`, `run()` — reuse for SF data seeding
- `~/projects/snow-meta-tool/hooks/postprovision.py` — SN agent creation pattern (line 474) for reference
- `~/projects/snow-meta-tool/scripts/seed_test_data.py` — SN data seeding pattern (httpx + basic auth) to adapt
- `~/projects/snow-meta-tool/scripts/test_e2e_tokens.py` — E2E test pattern to adapt for Customer 360
- `~/projects/snow-meta-tool/DEMO_DATA_SETUP.md` — complete correlated demo data spec (SF + SN)
- `~/projects/snow-meta-tool/TEST_PROMPTS.md` — Scenario 10 (cross-system prompts) to adapt
