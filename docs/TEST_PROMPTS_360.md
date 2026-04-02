# Test Prompts — Customer 360 Agent

Cross-system test scenarios for manual testing with the Customer 360 agent.
Requires demo data from `scripts/seed_demo_data.py` (see `docs/DEMO_DATA_SETUP.md`).

---

## 1. Unified Lookup

> Give me a Customer 360 view for Contoso Ltd

**Expected:** Agent queries SF for account details, contacts, opportunities, cases; then queries SN for incidents, problems, changes mentioning Contoso. Presents a unified view.

---

## 2. Revenue at Risk

> We have a P1 incident about API gateway failures. Which SF accounts and open opportunities are affected?

**Expected:** Agent finds the P1 payment processing incident in SN, identifies Northwind Traders from the description, queries SF for their account and open opportunities ($180K POS Upgrade), and highlights revenue at risk.

---

## 3. Meeting Prep

> Prepare me for my QBR with Acme Corp — pull everything from both systems

**Expected:** Agent pulls Acme Corp account, contacts (Sarah Chen, James Wilson), opportunities ($450K Platform Expansion), cases (API timeout, data export), and SN incidents (504 errors, export failures). Synthesizes into a meeting brief.

---

## 4. Change Risk Assessment

> We're planning a billing upgrade Saturday. Check the SN change request and SF accounts with upcoming renewals

**Expected:** Agent finds the "Upgrade billing system to v4.2" change request in SN, then checks SF for accounts with active deals that could be affected (Northwind POS Upgrade, Contoso Analytics Add-on).

---

## 5. Executive Summary

> Cross-system report: total open P1 incidents, total pipeline value, and for each P1, identify impacted accounts with open deals

**Expected:** Agent queries SN for P1 incidents, SF for all open opportunities, cross-references by company name, and produces a ranked report with pipeline values.

---

## 6. Proactive Outreach

> Acme Corp called about portal issues. Pull their full profile from both systems

**Expected:** Agent queries SF for Acme Corp account, contacts, all cases; SN for all incidents mentioning Acme Corp. Provides full customer context for the support call.

---

## 7. Case-Incident Correlation

> Show me all SF cases and SN incidents for Fabrikam from the last 30 days — are any related?

**Expected:** Agent queries both systems for Fabrikam Inc. Likely finds no incidents (Fabrikam is a Prospect with no correlated SN data). Agent explains the absence.

---

## Tips

- Start with scenario 1 (Unified Lookup) to verify both MCP tools are working
- Scenarios 2 and 5 test revenue correlation — they need both SF opportunities and SN incidents
- Scenario 4 tests change risk — needs SN change requests and SF opportunities with close dates
- Scenario 7 is a negative test — Fabrikam has no SN data
