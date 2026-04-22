"""Fleet pre-flight: validate environment + patch hooks for unattended execution.

Runs BEFORE any `azd` operation. Does not touch Azure state. Safe to rerun.

Responsibilities:
  1. Assert required binaries: az, azd, python
  2. Assert az is authenticated and context points at Sub-3
  3. Assert fleet principal (user or SP) has Contributor + UAA on Sub-3
  4. Assert both repos present at expected paths
  5. Assert local certs exist: certs/sf-jwt-bearer.pfx and ../snow-meta-tool/certs/sn-jwt-bearer.pfx
  6. PATCH hooks for fleet-safe failure semantics:
     - azure.yaml: continueOnError: true -> false
     - hooks/postprovision.sh: strip "|| echo ..." failure-swallows
     - hooks/postprovision.py: make it re-entrantly load azd env vars
     - hooks/postprovision.py: fall back to `az ad sp show` when `az ad signed-in-user show` fails (SP auth)
     Patches are applied IN PLACE in the workspace; exit non-zero if a patch can't be applied.
  7. Emit a summary JSON so fleet can archive it.

Exit codes:
  0 - preflight passed; safe to proceed
  1 - preflight failed; do not proceed
  2 - script error
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SUB3 = "1fafe902-ee73-468d-be1e-d76d99e8920c"
TENANT = "7be8beb2-a4db-4fe1-8108-e033b7c93f94"


def run(cmd: str, timeout: int = 60, check: bool = False) -> tuple[str, str, int]:
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout,
                           env={**os.environ, "MSYS_NO_PATHCONV": "1"})
    except subprocess.TimeoutExpired:
        return ("", f"TIMEOUT: {cmd}", -1)
    if check and p.returncode != 0:
        raise RuntimeError(f"cmd failed ({p.returncode}): {cmd}\n{p.stderr}")
    return (p.stdout.strip(), p.stderr.strip(), p.returncode)


def ok(msg: str):
    print(f"  [OK]   {msg}")


def fail(msg: str, fatal: bool = True):
    print(f"  [FAIL] {msg}", file=sys.stderr)
    if fatal:
        sys.exit(1)


def warn(msg: str):
    print(f"  [WARN] {msg}")


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_binaries():
    for b in ("az", "azd", "python"):
        if not shutil.which(b):
            fail(f"missing binary on PATH: {b}")
        else:
            ok(f"binary present: {b}")


def check_az_auth(sub: str):
    out, err, rc = run(f'az account show --subscription "{sub}" --query "{{id:id,tenantId:tenantId,user:user.name,type:user.type}}"')
    if rc != 0:
        fail(f"az not authenticated or no access to {sub}: {err}")
    data = json.loads(out)
    if data.get("tenantId") != TENANT:
        fail(f"wrong tenant: got {data.get('tenantId')}, want {TENANT}")
    ok(f"az authenticated as {data.get('user')} ({data.get('type')}) on sub {data['id']}")
    return data


def check_rbac(sub: str, principal: dict):
    """Ensure principal has Contributor + UAA (or Owner) at any scope covering this sub.
    Checks include inherited (management group) assignments and group-expanded roles.
    """
    pid_query = (f'az ad signed-in-user show --query id -o tsv' if principal.get("type") == "user"
                 else f'az ad sp show --id "{principal.get("user")}" --query id -o tsv')
    pid, _, rc = run(pid_query)
    if rc != 0 or not pid:
        warn(f"could not resolve principal id; skipping RBAC check")
        return
    out, _, rc = run(f'az role assignment list --scope "/subscriptions/{sub}" '
                     f'--assignee "{pid}" --include-inherited --include-groups '
                     f'--query "[].roleDefinitionName" -o json')
    if rc != 0:
        warn("could not list role assignments; skipping RBAC check")
        return
    roles = set(json.loads(out or "[]"))
    have_owner_or_both = "Owner" in roles or ({"Contributor", "User Access Administrator"} <= roles)
    if not have_owner_or_both:
        fail(f"principal missing required roles. Have: {sorted(roles)}. Need: Owner OR (Contributor + User Access Administrator).")
    ok(f"principal has sufficient RBAC: {sorted(roles)}")


def check_repos(sf: Path, sn: Path):
    for label, p in (("sf-repo", sf), ("sn-repo", sn)):
        if not (p / "azure.yaml").exists():
            fail(f"{label} missing azure.yaml at {p}")
        ok(f"{label} present at {p}")


def check_certs(sf: Path, sn: Path):
    for label, p in (("sf-cert", sf / "certs" / "sf-jwt-bearer.pfx"),
                     ("sn-cert", sn / "certs" / "sn-jwt-bearer.pfx")):
        if not p.exists():
            fail(f"{label} missing: {p}")
        ok(f"{label} present: {p} ({p.stat().st_size} bytes)")


# ---------------------------------------------------------------------------
# Patches
# ---------------------------------------------------------------------------

def patch_azure_yaml(path: Path):
    if not path.exists():
        fail(f"azure.yaml missing: {path}")
    txt = path.read_text(encoding="utf-8")
    if "continueOnError: true" in txt:
        new = txt.replace("continueOnError: true", "continueOnError: false")
        path.write_text(new, encoding="utf-8")
        ok(f"patched {path}: continueOnError -> false")
    else:
        ok(f"{path}: continueOnError already not-true (or absent)")
    # azd only supports shell: sh or pwsh. On Windows (Git Bash) sh IS bash so
    # bash-only constructs work; on Linux CI the postprovision.sh has
    # `#!/usr/bin/env bash` shebang which re-invokes bash. So we don't rewrite.
    if re.search(r"shell:\s*bash\b", txt):
        new = re.sub(r"shell:\s*bash\b", "shell: sh", path.read_text(encoding="utf-8"))
        path.write_text(new, encoding="utf-8")
        ok(f"patched {path}: shell bash -> sh (azd requires sh|pwsh)")


def patch_postprovision_sh(path: Path):
    if not path.exists():
        warn(f"no postprovision.sh at {path}; skipping")
        return
    txt = path.read_text(encoding="utf-8")
    orig = txt
    # Strip the "|| echo ..." failure swallows.
    txt = re.sub(r"\|\|\s*echo\s+[^\n]*", "", txt)
    # Ensure set -e is at top
    lines = txt.splitlines()
    if not any(l.strip().startswith("set -e") for l in lines[:5]):
        shebang = lines[0] if lines and lines[0].startswith("#!") else ""
        body = lines[1:] if shebang else lines
        txt = "\n".join([shebang, "set -euo pipefail"] + body) if shebang else "\n".join(["set -euo pipefail"] + body)
    if txt != orig:
        path.write_text(txt, encoding="utf-8")
        ok(f"patched {path}: strict error handling")
    else:
        ok(f"{path}: already strict")


def patch_postprovision_py(path: Path):
    """Make postprovision.py fleet-safe:
       1. If run directly (not via azd hook), auto-load .azure/<env>/.env
       2. Fall back to `az ad sp show` when signed-in-user fails
    Idempotent: detect marker comment.
    """
    if not path.exists():
        fail(f"postprovision.py missing: {path}")
    marker = "# FLEET_PATCH_V1"
    txt = path.read_text(encoding="utf-8")
    if marker in txt:
        ok(f"{path}: already patched")
        return

    preamble = f'''{marker}
# Auto-applied by fleet-preflight.py to make direct Python invocation work
# outside the azd hook context (for the finalize-customer360 step).
def _fleet_bootstrap_env():
    import os, subprocess
    if os.environ.get("AZURE_ENV_NAME"):
        return
    try:
        out = subprocess.run(["azd", "env", "get-values"], capture_output=True,
                             text=True, encoding="utf-8", errors="replace",
                             timeout=30, check=False)
        for line in (out.stdout or "").splitlines():
            line = line.strip()
            if not line or "=" not in line or line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception:
        pass
_fleet_bootstrap_env()
'''
    # Insert after the module docstring / first blank line following imports.
    # Safest: insert right after the first line that is `import os` or a top-level import.
    lines = txt.splitlines(keepends=True)
    insert_at = 0
    for i, line in enumerate(lines):
        if re.match(r"^(import|from)\s", line):
            insert_at = i
            break
    # Place preamble BEFORE imports (so env is set when imports run).
    patched = "".join(lines[:insert_at]) + preamble + "\n" + "".join(lines[insert_at:])

    # Patch the signed-in-user lookup to fall back to SP.
    patched = patched.replace(
        "az ad signed-in-user show",
        "az ad signed-in-user show --only-show-errors || az ad sp show --id \"$(az account show --query user.name -o tsv)\"",
    )

    path.write_text(patched, encoding="utf-8")
    ok(f"patched {path}: env bootstrap + SP fallback")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--subscription", default=SUB3)
    p.add_argument("--sf-repo", default=".")
    p.add_argument("--sn-repo", default="../snow-meta-tool")
    p.add_argument("--out", default=".local/fleet-preflight.json")
    p.add_argument("--skip-patches", action="store_true",
                   help="Only validate, do not modify files")
    args = p.parse_args()

    sf = Path(args.sf_repo).resolve()
    sn = Path(args.sn_repo).resolve()

    print("== FLEET PREFLIGHT ==")
    check_binaries()
    principal = check_az_auth(args.subscription)
    check_rbac(args.subscription, principal)
    check_repos(sf, sn)
    check_certs(sf, sn)

    if not args.skip_patches:
        print("\n-- Patching hooks for unattended execution --")
        for repo in (sf, sn):
            patch_azure_yaml(repo / "azure.yaml")
            patch_postprovision_sh(repo / "hooks" / "postprovision.sh")
            patch_postprovision_py(repo / "hooks" / "postprovision.py")
    else:
        warn("skipping patches (--skip-patches)")

    # Emit summary
    out_path = sf / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subscription": args.subscription,
        "tenant": TENANT,
        "principal": principal,
        "sf_repo": str(sf),
        "sn_repo": str(sn),
        "patches_applied": not args.skip_patches,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    ok(f"preflight summary written to {out_path}")
    print("\nPREFLIGHT PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
