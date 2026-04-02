"""Seed correlated demo data into Salesforce and ServiceNow for Customer 360 demos.

Seeds matching companies, contacts, opportunities, cases (SF) and incidents,
problems, change requests (SN) so the Customer 360 agent can correlate across systems.

Usage:
  python scripts/seed_demo_data.py \
    --sf-org <alias> \
    --sn-instance https://devXXXXX.service-now.com \
    --sn-admin-password <pw>

  python scripts/seed_demo_data.py --cleanup --sf-org <alias> \
    --sn-instance https://devXXXXX.service-now.com --sn-admin-password <pw>
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

# Add scripts dir to path for sf_utils
sys.path.insert(0, __file__ and __import__("os").path.dirname(__file__) or ".")
from sf_utils import get_access_token


# ---------------------------------------------------------------------------
# Salesforce REST helpers
# ---------------------------------------------------------------------------

def sf_query(instance_url, token, soql):
    """Run a SOQL query via REST API. Returns list of record dicts."""
    encoded = urllib.request.quote(soql, safe="")
    req = urllib.request.Request(
        f"{instance_url}/services/data/v62.0/query/?q={encoded}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read()).get("records", [])


def sf_create(instance_url, token, sobject, data):
    """Create a Salesforce record. Returns (id, None) or (None, error)."""
    req = urllib.request.Request(
        f"{instance_url}/services/data/v62.0/sobjects/{sobject}",
        data=json.dumps(data).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            return result.get("id"), None
    except urllib.error.HTTPError as e:
        return None, e.read().decode()


def sf_delete(instance_url, token, sobject, record_id):
    """Delete a Salesforce record by Id."""
    req = urllib.request.Request(
        f"{instance_url}/services/data/v62.0/sobjects/{sobject}/{record_id}",
        headers={"Authorization": f"Bearer {token}"},
        method="DELETE",
    )
    try:
        urllib.request.urlopen(req)
        return True
    except urllib.error.HTTPError:
        return False


# ---------------------------------------------------------------------------
# ServiceNow REST helpers
# ---------------------------------------------------------------------------

def sn_query(client_base, auth, table, query, fields="sys_id"):
    """Query ServiceNow table. Returns list of result dicts."""
    encoded = urllib.request.quote(query, safe="")
    req = urllib.request.Request(
        f"{client_base}/api/now/table/{table}"
        f"?sysparm_query={encoded}&sysparm_fields={fields}&sysparm_limit=10",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    # Add basic auth
    import base64
    cred = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
    req.add_header("Authorization", f"Basic {cred}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read()).get("result", [])


def sn_create(client_base, auth, table, data):
    """Create a ServiceNow record. Returns (sys_id, number) or (None, error).

    Uses sysparm_input_display_value=true so reference fields (like company)
    accept display names instead of requiring sys_ids.
    """
    import base64
    cred = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
    req = urllib.request.Request(
        f"{client_base}/api/now/table/{table}?sysparm_input_display_value=true",
        data=json.dumps(data).encode(),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {cred}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read()).get("result", {})
            return result.get("sys_id"), result.get("number", "")
    except urllib.error.HTTPError as e:
        return None, e.read().decode()


def sn_delete(client_base, auth, table, sys_id):
    """Delete a ServiceNow record."""
    import base64
    cred = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
    req = urllib.request.Request(
        f"{client_base}/api/now/table/{table}/{sys_id}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Basic {cred}",
        },
        method="DELETE",
    )
    try:
        urllib.request.urlopen(req)
        return True
    except urllib.error.HTTPError:
        return False


# ---------------------------------------------------------------------------
# Demo data definitions
# ---------------------------------------------------------------------------

ACCOUNTS = [
    {"Name": "Acme Corp", "Industry": "Technology", "AnnualRevenue": 5000000, "Type": "Customer"},
    {"Name": "Northwind Traders", "Industry": "Retail", "AnnualRevenue": 2500000, "Type": "Customer"},
    {"Name": "Contoso Ltd", "Industry": "Financial Services", "AnnualRevenue": 12000000, "Type": "Customer"},
    {"Name": "Fabrikam Inc", "Industry": "Manufacturing", "AnnualRevenue": 800000, "Type": "Prospect"},
    {"Name": "Adventure Works", "Industry": "Healthcare", "AnnualRevenue": 3200000, "Type": "Customer"},
]

CONTACTS = [
    {"LastName": "Chen", "FirstName": "Sarah", "Email": "sarah.chen@acmecorp.com", "Title": "VP of Engineering", "Phone": "+1-555-0101", "_account": "Acme Corp"},
    {"LastName": "Wilson", "FirstName": "James", "Email": "james.wilson@acmecorp.com", "Title": "IT Director", "Phone": "+1-555-0102", "_account": "Acme Corp"},
    {"LastName": "Garcia", "FirstName": "Maria", "Email": "maria.garcia@northwind.com", "Title": "CTO", "Phone": "+1-555-0201", "_account": "Northwind Traders"},
    {"LastName": "Kim", "FirstName": "David", "Email": "david.kim@contoso.com", "Title": "Head of Operations", "Phone": "+1-555-0301", "_account": "Contoso Ltd"},
    {"LastName": "Zhang", "FirstName": "Lisa", "Email": "lisa.zhang@contoso.com", "Title": "CISO", "Phone": "+1-555-0302", "_account": "Contoso Ltd"},
    {"LastName": "Brown", "FirstName": "Tom", "Email": "tom.brown@adventureworks.com", "Title": "IT Manager", "Phone": "+1-555-0501", "_account": "Adventure Works"},
]

OPPORTUNITIES = [
    {"Name": "Acme Corp - Platform Expansion", "Amount": 450000, "StageName": "Negotiation/Review", "CloseDate": "2026-05-01", "Description": "Expanding API integration and adding 500 users", "_account": "Acme Corp"},
    {"Name": "Northwind POS Upgrade", "Amount": 180000, "StageName": "Proposal/Price Quote", "CloseDate": "2026-05-01", "Description": "Point-of-sale system upgrade with payment module", "_account": "Northwind Traders"},
    {"Name": "Contoso Enterprise License", "Amount": 1200000, "StageName": "Closed Won", "CloseDate": "2026-03-01", "Description": "3-year enterprise license renewal", "_account": "Contoso Ltd"},
    {"Name": "Contoso Analytics Add-on", "Amount": 350000, "StageName": "Qualification", "CloseDate": "2026-06-01", "Description": "Real-time analytics dashboard for trading desk", "_account": "Contoso Ltd"},
    {"Name": "Adventure Works HIPAA Module", "Amount": 280000, "StageName": "Negotiation/Review", "CloseDate": "2026-04-22", "Description": "HIPAA-compliant patient data module", "_account": "Adventure Works"},
]

CASES = [
    {"Subject": "API gateway timeout errors", "Priority": "High", "Status": "New", "Description": "Customer reporting intermittent 504 errors on the API gateway since Tuesday", "_account": "Acme Corp"},
    {"Subject": "Payment processing failures", "Priority": "Critical", "Status": "New", "Description": "Payment module returning errors during checkout — affecting store operations", "_account": "Northwind Traders"},
    {"Subject": "Report generation slow", "Priority": "Medium", "Status": "New", "Description": "Monthly risk reports taking 45+ minutes to generate, was under 5 minutes", "_account": "Contoso Ltd"},
    {"Subject": "Trading desk dashboard timeout", "Priority": "Medium", "Status": "New", "Description": "Trading desk analytics dashboard timeout during market hours", "_account": "Contoso Ltd"},
    {"Subject": "SSO login failures", "Priority": "High", "Status": "New", "Description": "Users unable to authenticate via SSO since the certificate update", "_account": "Adventure Works"},
    {"Subject": "Data export not working", "Priority": "Medium", "Status": "New", "Description": "Scheduled data exports failing silently — no error notification", "_account": "Acme Corp"},
]

SN_INCIDENTS = [
    {
        "short_description": "API gateway returning 504 timeout errors - multiple customers affected",
        "description": "Intermittent 504 errors on the API gateway since Tuesday morning. Affected customers include Acme Corp and several other enterprise accounts. Impact: API-dependent integrations failing for ~15% of requests.",
        "impact": "2", "urgency": "2", "category": "Software",
        "company": "Acme Corp",
    },
    {
        "short_description": "Payment processing service degraded - transaction failures",
        "description": "Payment processing module returning errors during high-volume periods. Customer reports from Northwind Traders confirm checkout failures. Business impact: Direct revenue loss for affected merchants.",
        "impact": "1", "urgency": "1", "category": "Software",
        "company": "Northwind Traders",
    },
    {
        "short_description": "Database performance degradation - slow report generation",
        "description": "Report generation queries running 10x slower than baseline. Likely related to the index rebuild scheduled last weekend. Multiple customers reporting slow dashboards including Contoso Ltd.",
        "impact": "2", "urgency": "3", "category": "Software",
        "company": "Contoso Ltd",
    },
    {
        "short_description": "SSO certificate rotation caused authentication failures",
        "description": "After the scheduled SSL certificate rotation, some customers are experiencing SSO login failures. Adventure Works confirmed affected. Root cause likely: old certificate not fully revoked in IdP.",
        "impact": "2", "urgency": "2", "category": "Network",
        "company": "Adventure Works",
    },
    {
        "short_description": "Scheduled data export jobs failing silently",
        "description": "Automated data export cron jobs failing without alerting. Discovered during review after customer complaint from Acme Corp. Affects nightly export pipeline for ~20 accounts.",
        "impact": "2", "urgency": "3", "category": "Software",
        "company": "Acme Corp",
    },
    {
        "short_description": "Network latency spike on EU-West region",
        "description": "Monitoring shows 3x latency increase on EU-West load balancers since last night. Could be affecting European customers including Contoso Ltd.",
        "impact": "2", "urgency": "2", "category": "Network",
        "company": "Contoso Ltd",
    },
]

SN_PROBLEMS = [
    {
        "short_description": "Recurring database performance degradation during report generation",
        "description": "Multiple incidents reported over the past 2 weeks (slow queries, dashboard timeouts). Suspected root cause: missing indexes after the database migration on March 1st. Affecting customers with large datasets including Contoso Ltd.",
        "impact": "2", "urgency": "2",
        "company": "Contoso Ltd",
    },
]

SN_CHANGES = [
    {
        "short_description": "Upgrade billing system to v4.2",
        "description": "Upgrade the billing and invoicing platform from v4.1 to v4.2. Includes payment gateway API changes and new tax calculation engine. Maintenance window: Saturday 2AM-6AM UTC. Rollback plan: Revert to v4.1 container image.",
        "type": "Normal", "impact": "2", "risk": "2",
        "company": "Northwind Traders",
    },
    {
        "short_description": "CRM system database migration",
        "description": "Migrate CRM database from PostgreSQL 14 to PostgreSQL 16. Includes schema changes for new analytics features. Estimated downtime: 2 hours. Affects all CRM integrations.",
        "type": "Normal", "impact": "2", "risk": "1",
        "company": "Contoso Ltd",
    },
]


# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------

def seed_salesforce(sf_org):
    """Seed Salesforce with demo accounts, contacts, opportunities, and cases."""
    token, instance_url = get_access_token(sf_org)
    if not token or not instance_url:
        print("ERROR: Could not get SF access token. Run: sf org login web -a <alias>")
        return False

    print(f"\n=== Seeding Salesforce ({instance_url}) ===\n")
    account_ids = {}

    # Accounts
    print(f"--- Accounts ({len(ACCOUNTS)}) ---")
    for acct in ACCOUNTS:
        existing = sf_query(instance_url, token, f"SELECT Id FROM Account WHERE Name = '{acct['Name']}' LIMIT 1")
        if existing:
            account_ids[acct["Name"]] = existing[0]["Id"]
            print(f"  EXISTS: {acct['Name']} ({existing[0]['Id']})")
            continue
        rec_id, err = sf_create(instance_url, token, "Account", acct)
        if rec_id:
            account_ids[acct["Name"]] = rec_id
            print(f"  CREATED: {acct['Name']} ({rec_id})")
        else:
            print(f"  FAILED: {acct['Name']} — {err}")

    # Contacts
    print(f"\n--- Contacts ({len(CONTACTS)}) ---")
    for contact in CONTACTS:
        acct_name = contact.pop("_account")
        acct_id = account_ids.get(acct_name)
        if not acct_id:
            print(f"  SKIP: {contact['FirstName']} {contact['LastName']} — no account ID for {acct_name}")
            contact["_account"] = acct_name
            continue
        existing = sf_query(instance_url, token, f"SELECT Id FROM Contact WHERE Email = '{contact['Email']}' LIMIT 1")
        if existing:
            print(f"  EXISTS: {contact['FirstName']} {contact['LastName']} ({existing[0]['Id']})")
            contact["_account"] = acct_name
            continue
        contact["AccountId"] = acct_id
        rec_id, err = sf_create(instance_url, token, "Contact", contact)
        if rec_id:
            print(f"  CREATED: {contact['FirstName']} {contact['LastName']} ({rec_id})")
        else:
            print(f"  FAILED: {contact['FirstName']} {contact['LastName']} — {err}")
        contact.pop("AccountId", None)
        contact["_account"] = acct_name

    # Opportunities
    print(f"\n--- Opportunities ({len(OPPORTUNITIES)}) ---")
    for opp in OPPORTUNITIES:
        acct_name = opp.pop("_account")
        acct_id = account_ids.get(acct_name)
        if not acct_id:
            print(f"  SKIP: {opp['Name']} — no account ID for {acct_name}")
            opp["_account"] = acct_name
            continue
        existing = sf_query(instance_url, token, f"SELECT Id FROM Opportunity WHERE Name = '{opp['Name']}' LIMIT 1")
        if existing:
            print(f"  EXISTS: {opp['Name']} ({existing[0]['Id']})")
            opp["_account"] = acct_name
            continue
        opp["AccountId"] = acct_id
        rec_id, err = sf_create(instance_url, token, "Opportunity", opp)
        if rec_id:
            print(f"  CREATED: {opp['Name']} ({rec_id})")
        else:
            print(f"  FAILED: {opp['Name']} — {err}")
        opp.pop("AccountId", None)
        opp["_account"] = acct_name

    # Cases
    print(f"\n--- Cases ({len(CASES)}) ---")
    for case in CASES:
        acct_name = case.pop("_account")
        acct_id = account_ids.get(acct_name)
        if not acct_id:
            print(f"  SKIP: {case['Subject']} — no account ID for {acct_name}")
            case["_account"] = acct_name
            continue
        existing = sf_query(
            instance_url, token,
            f"SELECT Id FROM Case WHERE Subject = '{case['Subject']}' AND AccountId = '{acct_id}' LIMIT 1",
        )
        if existing:
            print(f"  EXISTS: {case['Subject']} ({existing[0]['Id']})")
            case["_account"] = acct_name
            continue
        case["AccountId"] = acct_id
        rec_id, err = sf_create(instance_url, token, "Case", case)
        if rec_id:
            print(f"  CREATED: {case['Subject']} ({rec_id})")
        else:
            print(f"  FAILED: {case['Subject']} — {err}")
        case.pop("AccountId", None)
        case["_account"] = acct_name

    return True


def sn_ensure_companies(base, auth, company_names):
    """Ensure all referenced companies exist in ServiceNow core_company table.

    The company field on incident/problem/change_request is a reference field
    to core_company. sysparm_input_display_value=true accepts display names
    but does NOT auto-create missing companies — they silently resolve to NULL.
    """
    print(f"--- Companies ({len(company_names)}) ---")
    for name in sorted(company_names):
        existing = sn_query(base, auth, "core_company", f"name={name}", fields="sys_id,name")
        if existing:
            print(f"  EXISTS: {name}")
            continue
        sys_id, result = sn_create(base, auth, "core_company", {"name": name})
        if sys_id and not sys_id.startswith("{"):
            print(f"  CREATED: {name} ({sys_id})")
        else:
            print(f"  FAILED: {name} — {result}")


def seed_servicenow(sn_instance, sn_user, sn_password):
    """Seed ServiceNow with demo incidents, problems, and change requests."""
    base = sn_instance.rstrip("/")
    auth = (sn_user, sn_password)

    print(f"\n=== Seeding ServiceNow ({base}) ===\n")

    # Ensure all referenced companies exist in core_company table first
    company_names = set()
    for items in [SN_INCIDENTS, SN_PROBLEMS, SN_CHANGES]:
        for item in items:
            if "company" in item:
                company_names.add(item["company"])
    sn_ensure_companies(base, auth, company_names)

    # Incidents
    print(f"\n--- Incidents ({len(SN_INCIDENTS)}) ---")
    for inc in SN_INCIDENTS:
        existing = sn_query(base, auth, "incident",
                           f"short_descriptionLIKE{inc['short_description'][:40]}")
        if existing:
            print(f"  EXISTS: {inc['short_description'][:65]}")
            continue
        sys_id, number = sn_create(base, auth, "incident", inc)
        if sys_id and not sys_id.startswith("{"):
            print(f"  CREATED: {number} — {inc['short_description'][:55]}")
        else:
            print(f"  FAILED: {inc['short_description'][:55]} — {number}")

    # Problems
    print(f"\n--- Problems ({len(SN_PROBLEMS)}) ---")
    for prob in SN_PROBLEMS:
        existing = sn_query(base, auth, "problem",
                           f"short_descriptionLIKE{prob['short_description'][:40]}")
        if existing:
            print(f"  EXISTS: {prob['short_description'][:65]}")
            continue
        sys_id, number = sn_create(base, auth, "problem", prob)
        if sys_id and not sys_id.startswith("{"):
            print(f"  CREATED: {number} — {prob['short_description'][:55]}")
        else:
            print(f"  FAILED: {prob['short_description'][:55]} — {number}")

    # Change Requests
    print(f"\n--- Change Requests ({len(SN_CHANGES)}) ---")
    for chg in SN_CHANGES:
        existing = sn_query(base, auth, "change_request",
                           f"short_descriptionLIKE{chg['short_description'][:40]}")
        if existing:
            print(f"  EXISTS: {chg['short_description'][:65]}")
            continue
        sys_id, number = sn_create(base, auth, "change_request", chg)
        if sys_id and not sys_id.startswith("{"):
            print(f"  CREATED: {number} — {chg['short_description'][:55]}")
        else:
            print(f"  FAILED: {chg['short_description'][:55]} — {number}")

    return True


def cleanup_salesforce(sf_org):
    """Delete seeded demo data from Salesforce."""
    token, instance_url = get_access_token(sf_org)
    if not token or not instance_url:
        print("ERROR: Could not get SF access token.")
        return

    print(f"\n=== Cleaning up Salesforce ({instance_url}) ===\n")
    account_names = [a["Name"] for a in ACCOUNTS]
    name_list = ",".join(f"'{n}'" for n in account_names)

    # Delete cases, opps, contacts first (children), then accounts
    for obj, query in [
        ("Case", f"SELECT Id FROM Case WHERE Account.Name IN ({name_list})"),
        ("Opportunity", f"SELECT Id FROM Opportunity WHERE Account.Name IN ({name_list})"),
        ("Contact", f"SELECT Id FROM Contact WHERE Account.Name IN ({name_list})"),
        ("Account", f"SELECT Id FROM Account WHERE Name IN ({name_list})"),
    ]:
        records = sf_query(instance_url, token, query)
        if records:
            print(f"  Deleting {len(records)} {obj} records...")
            for rec in records:
                sf_delete(instance_url, token, obj, rec["Id"])
        else:
            print(f"  No {obj} records to delete")


def cleanup_servicenow(sn_instance, sn_user, sn_password):
    """Delete seeded demo data from ServiceNow."""
    base = sn_instance.rstrip("/")
    auth = (sn_user, sn_password)

    print(f"\n=== Cleaning up ServiceNow ({base}) ===\n")

    for table, items in [
        ("incident", SN_INCIDENTS),
        ("problem", SN_PROBLEMS),
        ("change_request", SN_CHANGES),
    ]:
        for item in items:
            desc_prefix = item["short_description"][:40]
            records = sn_query(base, auth, table, f"short_descriptionLIKE{desc_prefix}")
            for rec in records:
                if sn_delete(base, auth, table, rec["sys_id"]):
                    print(f"  Deleted {table}: {desc_prefix}...")
                else:
                    print(f"  Failed to delete {table}: {desc_prefix}...")


def main():
    parser = argparse.ArgumentParser(description="Seed correlated demo data for Customer 360")
    parser.add_argument("--sf-org", default=None, help="Salesforce CLI org alias")
    parser.add_argument("--sn-instance", default=None, help="ServiceNow instance URL")
    parser.add_argument("--sn-admin-user", default="admin", help="ServiceNow admin username")
    parser.add_argument("--sn-admin-password", default=None, help="ServiceNow admin password")
    parser.add_argument("--cleanup", action="store_true", help="Delete seeded records instead of creating")
    parser.add_argument("--sf-only", action="store_true", help="Only seed/cleanup Salesforce")
    parser.add_argument("--sn-only", action="store_true", help="Only seed/cleanup ServiceNow")
    args = parser.parse_args()

    do_sf = not args.sn_only
    do_sn = not args.sf_only

    if do_sf and not args.sf_org:
        parser.error("--sf-org is required when seeding Salesforce")
    if do_sn and (not args.sn_instance or not args.sn_admin_password):
        parser.error("--sn-instance and --sn-admin-password are required when seeding ServiceNow")

    if args.cleanup:
        if do_sf:
            cleanup_salesforce(args.sf_org)
        if do_sn:
            cleanup_servicenow(args.sn_instance, args.sn_admin_user, args.sn_admin_password)
        print("\nCleanup complete.")
    else:
        if do_sf:
            seed_salesforce(args.sf_org)
        if do_sn:
            seed_servicenow(args.sn_instance, args.sn_admin_user, args.sn_admin_password)
        print("\nSeeding complete.")


if __name__ == "__main__":
    main()
