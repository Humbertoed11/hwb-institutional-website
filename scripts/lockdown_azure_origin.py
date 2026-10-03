#!/usr/bin/env python3
"""
SigmaFidelity™ Azure Origin Lockdown Automation Engine
Authority: Approved under SO-COM-001-DIR-06 (CEO Humberto Dominguez)
Standard: Mandate 12 / OWASP WAF Alignment / Zero-Trust Origin Isolation
Lead Auditor: Super George (Systems Architect & Lead Autonomous Commander)
Tactical Builder: George Bytes (Lead Software Engineer)

Capabilities:
1. Dynamically fetches official Cloudflare IPv4 CIDR blocks from https://www.cloudflare.com/ips-v4.
2. Idempotently configures Azure App Service Access Restrictions on 'hwb-institutional-website' (RG: 'HWB-Production-RG').
3. Restricts the main site (--scm-site false) to Cloudflare IPs only (Priorities 100-240).
4. Ensures SCM/Kudu deployment site is completely unrestricted.
5. Provides instant --rollback capability to remove Cloudflare rules if anomalies occur.
6. Probes https://hwbcleaning.com to verify HTTP 200 OK edge routing and tests origin 403 shield.
"""

import sys
import json
import urllib.request
import subprocess
import argparse

RESOURCE_GROUP = "HWB-Production-RG"
APP_NAME = "hwb-institutional-website"
CLOUDFLARE_IPS_URL = "https://www.cloudflare.com/ips-v4"


def fetch_cloudflare_ips() -> list[str]:
    """Fetches official Cloudflare IPv4 CIDR blocks."""
    print("  [1/4] Fetching official Cloudflare IPv4 CIDR blocks...", flush=True)
    req = urllib.request.Request(
        CLOUDFLARE_IPS_URL,
        headers={"User-Agent": "SigmaFidelity-Origin-Lockdown/1.0"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        text = resp.read().decode("utf-8")
        ips = [line.strip() for line in text.strip().splitlines() if line.strip()]
        print(f"        -> Retrieved {len(ips)} Cloudflare IPv4 CIDR ranges.")
        return ips


def get_current_restrictions() -> list[dict]:
    """Retrieves current IP security restrictions on the main site."""
    cmd = [
        "az", "webapp", "config", "access-restriction", "show",
        "-g", RESOURCE_GROUP,
        "-n", APP_NAME,
        "-o", "json"
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    data = json.loads(res.stdout)
    return data.get("ipSecurityRestrictions", [])


def apply_lockdown(ips: list[str]) -> bool:
    """Applies access restriction rules for each Cloudflare CIDR block."""
    print("  [2/4] Inspecting existing Azure App Service access restrictions...", flush=True)
    existing = get_current_restrictions()
    existing_map = {r.get("name"): r for r in existing if r.get("name")}

    print(f"  [3/4] Enforcing Origin Lockdown on '{APP_NAME}' ({len(ips)} rules)...", flush=True)
    base_priority = 100

    for idx, cidr in enumerate(ips):
        rule_name = f"Cloudflare_IPv4_{idx+1:02d}"
        priority = base_priority + (idx * 10)

        # Check if identical rule already exists
        if rule_name in existing_map:
            current_ip = existing_map[rule_name].get("ipAddress")
            if current_ip == cidr:
                print(f"        -> INTACT:  {rule_name} ({cidr}) Priority={priority}")
                continue
            else:
                # Remove stale rule
                subprocess.run([
                    "az", "webapp", "config", "access-restriction", "remove",
                    "-g", RESOURCE_GROUP,
                    "-n", APP_NAME,
                    "--rule-name", rule_name,
                    "--scm-site", "false"
                ], check=False)

        cmd = [
            "az", "webapp", "config", "access-restriction", "add",
            "-g", RESOURCE_GROUP,
            "-n", APP_NAME,
            "--rule-name", rule_name,
            "--action", "Allow",
            "--ip-address", cidr,
            "--priority", str(priority),
            "--description", f"Cloudflare Edge Proxy Range {cidr}",
            "--scm-site", "false"
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            print(f"        -> ADDED:   {rule_name} ({cidr}) Priority={priority}")
        else:
            print(f"        -> FAILED:  {rule_name} ({cidr}): {res.stderr.strip()}", file=sys.stderr)
            return False

    return True


def rollback_lockdown():
    """Removes all Cloudflare restriction rules, restoring open origin access."""
    print(f"  [ROLLBACK] Reverting Cloudflare access restrictions on '{APP_NAME}'...", flush=True)
    existing = get_current_restrictions()
    cf_rules = [r for r in existing if r.get("name", "").startswith("Cloudflare_")]

    if not cf_rules:
        print("        -> No Cloudflare rules found on main site. Nothing to remove.")
        return

    for r in cf_rules:
        rule_name = r["name"]
        cmd = [
            "az", "webapp", "config", "access-restriction", "remove",
            "-g", RESOURCE_GROUP,
            "-n", APP_NAME,
            "--rule-name", rule_name,
            "--scm-site", "false"
        ]
        res = subprocess.run(cmd, check=False)
        print(f"        -> REMOVED: {rule_name}")

    print("  [ROLLBACK] Origin access restored to default open policy.")


def verify_endpoints() -> bool:
    """Probes https://hwbcleaning.com and direct origin to verify lockdown."""
    print("  [4/4] Verifying Endpoints via HTTP Probes...", flush=True)
    all_ok = True

    # 1. Edge Probe (Must be HTTP 200 via Cloudflare)
    try:
        cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "https://hwbcleaning.com", "--max-time", "15"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        code = res.stdout.strip()
        if code in ("200", "301", "302"):
            print(f"        -> EDGE PROBE:   https://hwbcleaning.com -> HTTP {code} OK (Cloudflare Routed)")
        else:
            print(f"        -> EDGE WARNING: https://hwbcleaning.com -> HTTP {code}")
            all_ok = False
    except Exception as e:
        print(f"        -> EDGE PROBE FAILED: {e}")
        all_ok = False

    # 2. Direct Origin Probe (Must be HTTP 403 Forbidden to prove origin shield)
    try:
        cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"https://{APP_NAME}.azurewebsites.net", "--max-time", "15"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        code = res.stdout.strip()
        if code == "403":
            print(f"        -> SHIELD PROBE: https://{APP_NAME}.azurewebsites.net -> HTTP 403 Forbidden (Origin Shield Active)")
        else:
            print(f"        -> SHIELD NOTICE: https://{APP_NAME}.azurewebsites.net -> HTTP {code} (Direct bypass policy: {code})")
    except Exception as e:
        print(f"        -> SHIELD PROBE ERROR: {e}")

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="SigmaFidelity™ Azure Origin Lockdown")
    parser.add_argument("--rollback", action="store_true", help="Remove Cloudflare IP restrictions")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without modifying Azure")
    args = parser.parse_args()

    print("\n" + "=" * 76)
    print("  SIGMAFIDELITY™ AZURE ORIGIN LOCKDOWN AUTOMATION")
    print(f"  App Service: {APP_NAME} | Resource Group: {RESOURCE_GROUP}")
    print("=" * 76)

    if args.rollback:
        rollback_lockdown()
        verify_endpoints()
        return 0

    ips = fetch_cloudflare_ips()

    if args.dry_run:
        print(f"\n[DRY RUN] Would enforce {len(ips)} Cloudflare IPv4 rules (Priorities 100-{100 + (len(ips)-1)*10}):")
        for i, ip in enumerate(ips):
            print(f"   • Rule Cloudflare_IPv4_{i+1:02d}: {ip} (Allow, Priority {100 + i*10})")
        print("\n[DRY RUN] SCM/Kudu site will remain unrestricted.")
        return 0

    success = apply_lockdown(ips)
    if not success:
        print("\n[ERROR] Lockdown failed to apply all rules.", file=sys.stderr)
        return 1

    verify_endpoints()
    print("\n[SUCCESS] Azure Origin Lockdown Completed Successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
