# Demo Data Setup — Customer 360

To run the Customer 360 cross-system scenarios, both Salesforce and ServiceNow need **correlated data** — the same companies, contacts, and issues referenced across CRM and ITSM. The Customer 360 agent links them by matching company names, email domains, and keywords in descriptions.

> **Key principle:** There's no direct integration between the systems. The agent correlates data by recognizing that "Acme Corp" in a Salesforce Account is the same "Acme Corp" mentioned in a ServiceNow incident description.

---

## Automated Seeding

The fastest way to set up demo data:

```bash
python scripts/seed_demo_data.py \
  --sf-org <alias> \
  --sn-instance https://devXXXXX.service-now.com \
  --sn-admin-password <pw>
```

To clean up:

```bash
python scripts/seed_demo_data.py --cleanup \
  --sf-org <alias> \
  --sn-instance https://devXXXXX.service-now.com \
  --sn-admin-password <pw>
```

You can also seed only one system with `--sf-only` or `--sn-only`.

> **Important:** The script automatically pre-creates companies in ServiceNow's `core_company` table before seeding incidents. The `company` field on incidents is a **reference field** — if the company doesn't exist in `core_company`, the field silently resolves to NULL even with `sysparm_input_display_value=true`.

---

## Correlation Strategy

| Link Method | Salesforce Field | ServiceNow Field | Used By |
|---|---|---|---|
| Company name | `Account.Name` | Incident description text | Most prompts |
| Email domain | `Contact.Email` | Caller email | Customer lookup |
| Keywords | `Case.Subject`, `Opportunity.Description` | `incident.short_description` | Pattern matching |

---

## Salesforce Data

### Accounts (5 companies)

| Account Name | Industry | Annual Revenue | Type |
|---|---|---|---|
| Acme Corp | Technology | $5,000,000 | Customer |
| Northwind Traders | Retail | $2,500,000 | Customer |
| Contoso Ltd | Financial Services | $12,000,000 | Customer |
| Fabrikam Inc | Manufacturing | $800,000 | Prospect |
| Adventure Works | Healthcare | $3,200,000 | Customer |

### Contacts (6 contacts, 1-2 per account)

| Name | Account | Email | Title |
|---|---|---|---|
| Sarah Chen | Acme Corp | sarah.chen@acmecorp.com | VP of Engineering |
| James Wilson | Acme Corp | james.wilson@acmecorp.com | IT Director |
| Maria Garcia | Northwind Traders | maria.garcia@northwind.com | CTO |
| David Kim | Contoso Ltd | david.kim@contoso.com | Head of Operations |
| Lisa Zhang | Contoso Ltd | lisa.zhang@contoso.com | CISO |
| Tom Brown | Adventure Works | tom.brown@adventureworks.com | IT Manager |

### Opportunities (5 deals, $180K-$1.2M)

| Opportunity | Account | Amount | Stage |
|---|---|---|---|
| Acme Corp - Platform Expansion | Acme Corp | $450,000 | Negotiation |
| Northwind POS Upgrade | Northwind Traders | $180,000 | Proposal |
| Contoso Enterprise License | Contoso Ltd | $1,200,000 | Closed Won |
| Contoso Analytics Add-on | Contoso Ltd | $350,000 | Qualification |
| Adventure Works HIPAA Module | Adventure Works | $280,000 | Negotiation |

### Cases (6 open cases, correlated to SN incidents)

| Case Subject | Account | Priority | Correlates With SN |
|---|---|---|---|
| API gateway timeout errors | Acme Corp | High | API gateway 504 incident |
| Payment processing failures | Northwind Traders | Critical | Payment service incident |
| Report generation slow | Contoso Ltd | Medium | DB performance incident |
| Trading desk dashboard timeout | Contoso Ltd | Medium | DB performance incident |
| SSO login failures | Adventure Works | High | SSO certificate incident |
| Data export not working | Acme Corp | Medium | Data export jobs incident |

---

## ServiceNow Data

### Incidents (6 incidents, P1-P3)

| Short Description | Priority | Correlates With SF |
|---|---|---|
| API gateway returning 504 timeout errors | P2 | Acme Corp case |
| Payment processing service degraded | P1 | Northwind case |
| Database performance degradation - slow reports | P3 | Contoso cases |
| SSO certificate rotation caused auth failures | P2 | Adventure Works case |
| Scheduled data export jobs failing silently | P3 | Acme Corp case |
| Network latency spike on EU-West region | P2 | Contoso accounts |

### Problems (1)

| Short Description | Impact |
|---|---|
| Recurring database performance degradation during report generation | High |

### Change Requests (2)

| Short Description | Risk |
|---|---|
| Upgrade billing system to v4.2 | Moderate |
| CRM system database migration | High |

---

## Data Validation

After seeding, verify with the Customer 360 agent:

1. **SF side:** "Show me all open support cases with account name and priority"
2. **SN side:** "Show me all open P1 and P2 incidents with descriptions"
3. **Cross-system:** "Give me a Customer 360 view for Acme Corp"

---

## Prompt-to-Data Mapping

| Scenario | Salesforce Data | ServiceNow Data |
|---|---|---|
| Unified lookup | Account + contacts + opps + cases | Incidents mentioning company |
| Revenue at risk | Opportunities with amounts | P1/P2 incidents with customer names |
| Case-incident correlation | Cases (report slow) | Incidents (DB performance) |
| Change risk + renewals | Opportunities with close dates | Change requests (billing upgrade) |
| Meeting prep | Account + opps | Active incidents for company |
| Executive summary | All pipeline value | All P1 incidents |
