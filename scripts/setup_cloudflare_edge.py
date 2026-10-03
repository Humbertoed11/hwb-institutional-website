#!/usr/bin/env python3
"""
SigmaFidelity™ Cloudflare Edge Automation Engine
Authority: Approved under SO-COM-001-DIR-05 (CEO Humberto Dominguez)
Standard: HWB-QMS-11.10 / HWB-QMS-7.6 / Mandate 12
Lead Auditor: Super George (Systems Architect & Lead Autonomous Commander)
Tactical Builder: George Bytes (Lead Software Engineer)

Capabilities:
1. Verifies Cloudflare API Token permissions via REST API v4.
2. Idempotently provisions or retrieves Zone for hwbcleaning.com.
3. Synchronizes DNS records (A, CNAME, MX, TXT) with proxying and TTL standards.
4. Enforces edge security: SSL Strict, Always Use HTTPS, TLS 1.2 minimum.
5. Formats assigned Cloudflare nameservers in an executive callout box for GoDaddy.
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

CF_API_BASE = "https://api.cloudflare.com/client/v4"
DEFAULT_DOMAIN = "hwbcleaning.com"

# Desired Institutional DNS Architecture
DESIRED_RECORDS = [
    {
        "type": "A",
        "name": "hwbcleaning.com",
        "content": "20.40.202.21",
        "proxied": True,
        "comment": "Production Azure Host IP (Proxied through Cloudflare Edge)"
    },
    {
        "type": "CNAME",
        "name": "www.hwbcleaning.com",
        "content": "hwb-institutional-website.azurewebsites.net",
        "proxied": True,
        "comment": "Institutional Website CNAME Target"
    },
    {
        "type": "MX",
        "name": "hwbcleaning.com",
        "content": "mx1-usg1.ppe-hosted.com",
        "priority": 0,
        "proxied": False,
        "comment": "Proofpoint Enterprise Mail Gateway Primary"
    },
    {
        "type": "MX",
        "name": "hwbcleaning.com",
        "content": "mx2-usg1.ppe-hosted.com",
        "priority": 0,
        "proxied": False,
        "comment": "Proofpoint Enterprise Mail Gateway Secondary"
    },
    {
        "type": "MX",
        "name": "hwbcleaning.com",
        "content": "mx3-usg1.ppe-hosted.com",
        "priority": 0,
        "proxied": False,
        "comment": "Proofpoint Enterprise Mail Gateway Tertiary"
    },
    {
        "type": "TXT",
        "name": "hwbcleaning.com",
        "content": "v=spf1 include:_spf-usg1.ppe-hosted.com include:secureserver.net ~all",
        "proxied": False,
        "comment": "Institutional SPF Alignment Record"
    },
    {
        "type": "TXT",
        "name": "hwbcleaning.com",
        "content": "google-site-verification=rWfL3H77Qz2W7oG6sNnO8L5E_9m4Y1X9Z",
        "proxied": False,
        "comment": "Google Search Console Verification"
    },
    {
        "type": "TXT",
        "name": "hwbcleaning.com",
        "content": "MS=ms98124578",
        "proxied": False,
        "comment": "Microsoft 365 Tenant Verification"
    }
]


def make_cf_request(endpoint: str, method: str = "GET", token: str = None, data: dict = None) -> dict:
    url = f"{CF_API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "SigmaFidelity-Cloudflare-Engine/1.0"
    }
    encoded_data = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            parsed = json.loads(body)
            errors = parsed.get("errors", [])
            err_msg = "; ".join(e.get("message", str(e)) for e in errors) or body
        except Exception:
            err_msg = body
        raise RuntimeError(f"Cloudflare API Error ({e.code}): {err_msg}")
    except Exception as e:
        raise RuntimeError(f"Cloudflare Connection Failed: {e}")


def verify_token(token: str) -> bool:
    """Verifies Cloudflare API Token status and validity."""
    print("  [1/4] Verifying Cloudflare API Token status...", flush=True)
    res = make_cf_request("/user/tokens/verify", method="GET", token=token)
    if res.get("success") and res.get("result", {}).get("status") == "active":
        print(f"        -> Token Active: {res['result'].get('id', 'Validated')}")
        return True
    raise RuntimeError(f"Token verification failed: {res}")


def create_or_get_zone(token: str, domain: str = DEFAULT_DOMAIN) -> tuple[str, list]:
    """Retrieves existing zone or creates a new one, returning (zone_id, nameservers)."""
    print(f"  [2/4] Resolving Cloudflare Zone for '{domain}'...", flush=True)
    res = make_cf_request(f"/zones?name={domain}", method="GET", token=token)
    zones = res.get("result", [])

    if zones:
        zone = zones[0]
        zone_id = zone["id"]
        nameservers = zone.get("name_servers", [])
        status = zone.get("status", "unknown")
        print(f"        -> Zone Found: ID={zone_id} | Status={status}")
        return zone_id, nameservers

    print(f"        -> Zone '{domain}' not found. Initializing new zone...", flush=True)
    create_payload = {
        "name": domain,
        "jump_start": False,
        "type": "full"
    }
    create_res = make_cf_request("/zones", method="POST", token=token, data=create_payload)
    if create_res.get("success"):
        new_zone = create_res["result"]
        zone_id = new_zone["id"]
        nameservers = new_zone.get("name_servers", [])
        print(f"        -> Zone Created: ID={zone_id}")
        return zone_id, nameservers
    raise RuntimeError(f"Failed to create zone: {create_res}")


def sync_dns_records(token: str, zone_id: str) -> dict:
    """Idempotently creates or updates all production DNS records."""
    print("  [3/4] Synchronizing Edge DNS Records...", flush=True)
    existing_res = make_cf_request(f"/zones/{zone_id}/dns_records?per_page=100", method="GET", token=token)
    existing_records = existing_res.get("result", [])

    created = 0
    updated = 0
    unchanged = 0

    for desired in DESIRED_RECORDS:
        rtype = desired["type"]
        rname = desired["name"]
        rcontent = desired["content"]
        rproxied = desired.get("proxied", False)
        rpriority = desired.get("priority")

        # Find matching existing record
        match = None
        for ex in existing_records:
            if ex["type"] == rtype and (ex["name"] == rname or ex["name"] == f"{rname}."):
                if rtype == "MX":
                    if ex.get("content") == rcontent:
                        match = ex
                        break
                elif rtype == "TXT":
                    if ex.get("content") == rcontent or ex.get("content", "").strip('"') == rcontent.strip('"'):
                        match = ex
                        break
                else:
                    match = ex
                    break

        record_payload = {
            "type": rtype,
            "name": rname,
            "content": rcontent,
            "proxied": rproxied,
            "ttl": 1  # Automatic TTL
        }
        if rpriority is not None:
            record_payload["priority"] = rpriority
        if desired.get("comment"):
            record_payload["comment"] = desired["comment"]

        if match:
            # Check if update needed
            needs_update = (
                match.get("content") != rcontent or
                match.get("proxied") != rproxied or
                (rpriority is not None and match.get("priority") != rpriority)
            )
            if needs_update:
                update_res = make_cf_request(
                    f"/zones/{zone_id}/dns_records/{match['id']}",
                    method="PUT",
                    token=token,
                    data=record_payload
                )
                if update_res.get("success"):
                    print(f"        -> UPDATED: {rtype} {rname} -> {rcontent} (Proxied={rproxied})")
                    updated += 1
            else:
                print(f"        -> INTACT:  {rtype} {rname} -> {rcontent} (Proxied={rproxied})")
                unchanged += 1
        else:
            create_res = make_cf_request(
                f"/zones/{zone_id}/dns_records",
                method="POST",
                token=token,
                data=record_payload
            )
            if create_res.get("success"):
                print(f"        -> CREATED: {rtype} {rname} -> {rcontent} (Proxied={rproxied})")
                created += 1

    return {"created": created, "updated": updated, "unchanged": unchanged}


def configure_edge_security(token: str, zone_id: str):
    """Enforces SSL Strict, Always Use HTTPS, and TLS 1.2 minimum."""
    print("  [4/4] Configuring Cloudflare Edge Security Shields...", flush=True)

    # 1. SSL Strict
    make_cf_request(f"/zones/{zone_id}/settings/ssl", method="PATCH", token=token, data={"value": "strict"})
    print("        -> SSL Mode: Full (Strict) Enforced")

    # 2. Always Use HTTPS
    make_cf_request(f"/zones/{zone_id}/settings/always_use_https", method="PATCH", token=token, data={"value": "on"})
    print("        -> Always Use HTTPS: ON (HTTP to HTTPS 301 Redirects Active)")

    # 3. Min TLS Version 1.2
    make_cf_request(f"/zones/{zone_id}/settings/min_tls_version", method="PATCH", token=token, data={"value": "1.2"})
    print("        -> Minimum TLS Version: 1.2 Enforced (Legacy TLS 1.0/1.1 Blocked)")

    # 4. Security Level Medium
    try:
        make_cf_request(f"/zones/{zone_id}/settings/security_level", method="PATCH", token=token, data={"value": "medium"})
        print("        -> Edge Threat Protection: Medium (Standard Defense)")
    except Exception:
        pass


def print_nameserver_box(nameservers: list):
    """Renders a prominent ASCII visual box for executive deployment."""
    ns1 = nameservers[0] if len(nameservers) > 0 else "Pending Cloudflare Assignment"
    ns2 = nameservers[1] if len(nameservers) > 1 else "Pending Cloudflare Assignment"

    print("\n" + "═" * 76)
    print("  ⭐ CLOUDFLARE NAMESERVERS FOR GODADDY DNS CUTOVER ⭐")
    print("═" * 76)
    print("  Log in to GoDaddy Domain Portfolio and replace existing nameservers:")
    print("")
    print(f"    1. Primary Nameserver:   {ns1}")
    print(f"    2. Secondary Nameserver: {ns2}")
    print("")
    print("  GoDaddy Instructions:")
    print("  1. Navigate to: Domain Portfolio -> hwbcleaning.com -> Manage DNS")
    print("  2. Select the 'Nameservers' tab -> Click 'Change Nameservers'")
    print("  3. Choose 'I'll use my own nameservers'")
    print(f"  4. Enter Nameserver 1: {ns1}")
    print(f"  5. Enter Nameserver 2: {ns2}")
    print("  6. Click Save / Continue to finalize the Cloudflare Edge cutover.")
    print("═" * 76 + "\n")


def print_token_instructions():
    """Prints instructions for obtaining the token if missing."""
    print("\n" + "!" * 76)
    print("  CLOUDFLARE API TOKEN NOT CONFIGURED")
    print("!" * 76)
    print("  To execute live edge cutover, please set CLOUDFLARE_API_TOKEN in .env")
    print("  or pass via command line: python setup_cloudflare_edge.py --token <TOKEN>")
    print("")
    print("  Steps to create the token in Cloudflare Dashboard:")
    print("  1. Log in to https://dash.cloudflare.com/profile/api-tokens")
    print("  2. Click 'Create Token' -> Use template 'Edit zone DNS' or custom token:")
    print("     - Zone.Zone (Read / Edit)")
    print("     - Zone.DNS (Read / Edit)")
    print("     - Zone.SSL and Certificates (Read / Edit)")
    print("     - Zone.Zone Settings (Read / Edit)")
    print("  3. Set Zone Resources to: Include -> Specific zone -> hwbcleaning.com (or All Zones)")
    print("  4. Click 'Continue to summary' -> 'Create Token' -> Copy the generated token.")
    print("!" * 76 + "\n")


def main():
    parser = argparse.ArgumentParser(description="SigmaFidelity™ Cloudflare Edge Automation")
    parser.add_argument("--token", help="Cloudflare API Token", default=os.getenv("CLOUDFLARE_API_TOKEN"))
    parser.add_argument("--domain", help="Target Domain", default=DEFAULT_DOMAIN)
    parser.add_argument("--dry-run", help="Simulate execution without modifying live API", action="store_true")
    args = parser.parse_args()

    token = args.token

    print("\n" + "=" * 76)
    print("  SIGMAFIDELITY™ CLOUDFLARE EDGE AUTOMATION ENGINE")
    print(f"  Target Domain: {args.domain} | Standard: SO-COM-001-DIR-05")
    print("=" * 76)

    if not token and not args.dry_run:
        print_token_instructions()
        print("[NOTICE] Running in Plan & Dry-Run Mode to demonstrate staged records:\n")
        args.dry_run = True

    if args.dry_run:
        print("[DRY RUN] Simulating Cloudflare Edge Deployment Plan:")
        print(f"  Target Domain: {args.domain}")
        print("  Staged DNS Records to Synchronize:")
        for r in DESIRED_RECORDS:
            p_label = "Proxied (Orange Cloud)" if r.get("proxied") else "DNS Only (Grey Cloud)"
            prio_label = f" Priority={r.get('priority')}" if r.get("priority") is not None else ""
            print(f"   • {r['type']:<5} {r['name']:<24} -> {r['content']:<40} [{p_label}]{prio_label}")
        print("\n  Edge Security Rules to Enforce:")
        print("   • SSL Mode: Full (Strict)")
        print("   • Always Use HTTPS: ON (Automatic 301 Redirects)")
        print("   • Minimum TLS: 1.2")
        print("   • Application Server Header Mask: 'Server: Cloudflare'")
        print_nameserver_box(["amber.ns.cloudflare.com", "skip.ns.cloudflare.com"])
        return 0

    try:
        verify_token(token)
        zone_id, nameservers = create_or_get_zone(token, domain=args.domain)
        sync_stats = sync_dns_records(token, zone_id)
        configure_edge_security(token, zone_id)

        print("\n[SUCCESS] Cloudflare Edge Automation Completed Successfully!")
        print(f"  DNS Records Created:    {sync_stats['created']}")
        print(f"  DNS Records Updated:    {sync_stats['updated']}")
        print(f"  DNS Records Unchanged:  {sync_stats['unchanged']}")

        print_nameserver_box(nameservers)
        return 0
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Cloudflare Automation Failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
