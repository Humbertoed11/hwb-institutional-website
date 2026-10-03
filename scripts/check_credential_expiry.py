#!/usr/bin/env python3
"""
⚡ SIGMAFIDELITY™ CREDENTIAL & SECRET EXPIRY SENTINEL CLI
Standard: SO-COM-001-DIR-09 / Mandate 12
Rack 4: Azure & Cloud Gateway Infrastructure
Lead Software Engineer: George Bytes (Tactical Builder)
Reporting to: Super George & CEO Humberto Dominguez

Monitors and audits all external API tokens, client secrets, and SSL certificates
to prevent silent expirations and unexpected service disruption.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone

# Setup module search paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Inside container support
if os.path.exists("/app/core/services/credential_sentinel.py") and "/app" not in sys.path:
    sys.path.insert(0, "/app")

from core.services.credential_sentinel import audit_all_credentials

# ANSI Color Palette
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
ORANGE = "\033[38;5;208m"
RED = "\033[31m"
PURPLE = "\033[35m"
GRAY = "\033[90m"


def render_bar(score: float, width: int = 30) -> str:
    filled = int(round((score / 100.0) * width))
    filled = max(0, min(width, filled))
    empty = width - filled
    if score >= 90:
        bar_color = GREEN
    elif score >= 75:
        bar_color = YELLOW
    else:
        bar_color = RED
    return f"{bar_color}{'█' * filled}{GRAY}{'░' * empty}{RESET} {BOLD}{score:.1f}%{RESET}"


def print_executive_dashboard(results: dict):
    score = results.get("health_score", 0.0)
    grade = results.get("letter_grade", "N/A")
    monitored = results.get("credentials_monitored_count", 0)
    healthy = results.get("credentials_healthy_count", 0)
    action_req = results.get("credentials_action_required", 0)
    creds = results.get("credentials", [])
    timestamp = results.get("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))

    print()
    print(f"{CYAN}{BOLD}========================================================================================{RESET}")
    print(f"{CYAN}{BOLD}  ⚡ HWB ENTERPRISE CREDENTIAL & SECRET EXPIRY SENTINEL{RESET}")
    print(f"{GRAY}  Standard: SO-COM-001-DIR-09 | Rack 4: Azure & Cloud Gateway | Lead: George Bytes{RESET}")
    print(f"{CYAN}{BOLD}========================================================================================{RESET}")
    print(f"  {BOLD}Telemetry Timestamp:{RESET}  {timestamp}")
    print(f"  {BOLD}Monitored Secrets:{RESET}    {monitored} credentials active in registry")
    print(f"  {BOLD}Fleet Health Score:{RESET}   {render_bar(score)} (Grade: {GREEN if score >= 85 else YELLOW}{grade}{RESET})")
    print(f"  {BOLD}Status Breakdown:{RESET}     {GREEN}{healthy} Healthy{RESET} | {RED if action_req > 0 else GRAY}{action_req} Action Required{RESET}")
    print(f"{CYAN}----------------------------------------------------------------------------------------{RESET}")

    # Table Header
    print(f"  {BOLD}{'#':<3} {'Credential / Token Name':<24} {'Service Target':<25} {'Days Left':<11} {'Status / Badge':<18}{RESET}")
    print(f"  {GRAY}{'-'*3} {'-'*24} {'-'*25} {'-'*11} {'-'*18}{RESET}")

    for idx, c in enumerate(creds, 1):
        name = c.get("name", "Unknown")[:24]
        service = c.get("service", "Unknown")[:25]
        days = c.get("days_remaining", 0)
        days_str = f"{days}d" if days < 900 else "Perpetual"
        badge = c.get("badge", "Unknown")
        action = c.get("action_required", False)

        if action:
            row_color = RED
            status_display = f"{RED}{badge}{RESET}"
        elif days < 30 and days >= 0:
            row_color = YELLOW
            status_display = f"{YELLOW}{badge}{RESET}"
        else:
            row_color = GREEN
            status_display = f"{GREEN}{badge}{RESET}"

        print(f"  {row_color}{idx:<3} {name:<24} {service:<25} {days_str:<11} {status_display}{RESET}")

    print(f"{CYAN}----------------------------------------------------------------------------------------{RESET}")

    # Detailed Action Section if any action is needed
    if action_req > 0:
        print(f"\n  {RED}{BOLD}🚨 REMEDIATION ACTION ITEMS REQUIRED:{RESET}")
        for c in creds:
            if c.get("action_required", False):
                print(f"  {RED}• [{c.get('name')}] ({c.get('service')}):{RESET}")
                print(f"    {YELLOW}Issue:{RESET}  {c.get('notes')}")
                print(f"    {YELLOW}Action:{RESET} Generate renewed token and update environment variable in .env.")
    else:
        print(f"\n  {GREEN}{BOLD}✨ ALL CREDENTIALS OPERATIONAL:{RESET} No imminent expirations or auth errors.")

    print(f"\n{CYAN}{BOLD}========================================================================================{RESET}\n")


def main():
    parser = argparse.ArgumentParser(description="HWB Credential & Secret Expiry Sentinel CLI")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--strict", action="store_true", help="Exit with non-zero exit code if any secret requires action")
    args = parser.parse_args()

    results = audit_all_credentials()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_executive_dashboard(results)

    if args.strict and results.get("credentials_action_required", 0) > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
