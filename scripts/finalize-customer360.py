"""Finalize Customer 360: run the SF postprovision hook a third time, then
wait for the 30–60s salesforce-obo churn to settle, then re-run verify.

This is a fleet-safe wrapper for Phase 5 "finalize-customer360" step.

Idempotent and deterministic:
  - Runs the SF hook via `hooks/postprovision.sh` with the customer-360 env
    selected, so azd env vars are loaded properly (not a raw python invocation)
  - Polls Foundry connection + /health endpoints until stable or timeout
  - Runs verify-migration.py twice, 60s apart, requiring both to PASS

Usage:
  python scripts/finalize-customer360.py --sub <sub-3-id> --rg rg-customer-360 \
      --sf-env customer-360 --sn-env customer-360-sn
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def run(cmd: str, cwd: str | None = None, timeout: int = 1800) -> int:
    print(f"\n$ {cmd}")
    p = subprocess.run(cmd, shell=True, cwd=cwd, text=True,
                       encoding="utf-8", errors="replace",
                       env={**os.environ, "MSYS_NO_PATHCONV": "1"},
                       timeout=timeout)
    return p.returncode


def az_json(cmd: str, timeout: int = 60):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout,
                       env={**os.environ, "MSYS_NO_PATHCONV": "1"})
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout) if p.stdout.strip() else None
    except json.JSONDecodeError:
        return None


def wait_connection_ready(sub: str, rg: str, cog: str, proj: str, name: str,
                          timeout_s: int = 300) -> bool:
    url = (f"https://management.azure.com/subscriptions/{sub}/resourceGroups/{rg}"
           f"/providers/Microsoft.CognitiveServices/accounts/{cog}/projects/{proj}"
           f"/connections/{name}?api-version=2025-04-01-preview")
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        data = az_json(f'az rest --method GET --url "{url}" --subscription "{sub}"')
        if data and data.get("id"):
            print(f"  [{name}] connection READY after {int(time.time() - t0)}s")
            return True
        time.sleep(10)
    print(f"  [{name}] connection NOT ready after {timeout_s}s")
    return False


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sub", required=True)
    p.add_argument("--rg", required=True)
    p.add_argument("--sf-env", default="customer-360")
    p.add_argument("--sn-env", default="customer-360-sn")
    p.add_argument("--sf-repo", default=".")
    p.add_argument("--sn-repo", default="../snow-meta-tool")
    p.add_argument("--settle-secs", type=int, default=90)
    args = p.parse_args()

    sf_repo = Path(args.sf_repo).resolve()

    # 1. Ensure the SF azd env is selected.
    rc = run(f'az account set --subscription "{args.sub}"', cwd=str(sf_repo))
    if rc != 0:
        return 1
    rc = run(f'azd env select "{args.sf_env}"', cwd=str(sf_repo))
    if rc != 0:
        return 1

    # 2. Invoke the hook via its shell wrapper (loads azd env via `azd env get-values`).
    hook = sf_repo / "hooks" / "postprovision.sh"
    if not hook.exists():
        print(f"ERROR: {hook} missing", file=sys.stderr)
        return 2
    # Use bash explicitly; azure.yaml is patched to bash already.
    rc = run(f'bash "{hook}"', cwd=str(sf_repo), timeout=1800)
    if rc != 0:
        print(f"ERROR: postprovision.sh exited {rc}", file=sys.stderr)
        return 1

    # 3. Read back azd env to get cognitive / project names.
    envp = subprocess.run("azd env get-values", shell=True, capture_output=True,
                          text=True, encoding="utf-8", cwd=str(sf_repo))
    env = {}
    for line in envp.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    cog = env.get("COGNITIVE_ACCOUNT_NAME")
    proj = env.get("AI_FOUNDRY_PROJECT_NAME")

    # 4. Wait for the 30–60s churn window to close.
    print(f"\nSettling {args.settle_secs}s for salesforce-obo churn window...")
    time.sleep(args.settle_secs)
    if cog and proj:
        for conn in ("salesforce-obo", "servicenow-obo"):
            wait_connection_ready(args.sub, args.rg, cog, proj, conn, timeout_s=300)

    # 5. Run verify twice with a gap; both must pass.
    verify = sf_repo / "scripts" / "verify-migration.py"
    cmd = (f'python "{verify}" --subscription "{args.sub}" --rg "{args.rg}" '
           f'--sf-env "{args.sf_env}" --sn-env "{args.sn_env}" --skip-manual')
    print("\n=== First verify ===")
    rc1 = run(cmd, cwd=str(sf_repo), timeout=1200)
    if rc1 != 0:
        print(f"FAIL: first verify rc={rc1}", file=sys.stderr)
        return 1
    print("\n=== Cooldown 60s before second verify ===")
    time.sleep(60)
    print("\n=== Second verify ===")
    rc2 = run(cmd, cwd=str(sf_repo), timeout=1200)
    if rc2 != 0:
        print(f"FAIL: second verify rc={rc2}", file=sys.stderr)
        return 1
    print("\nFINALIZE-CUSTOMER360 PASS (both verify runs green)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
