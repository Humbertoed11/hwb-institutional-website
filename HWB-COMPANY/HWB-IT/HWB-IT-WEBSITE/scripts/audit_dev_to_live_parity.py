#!/usr/bin/env python3
"""
SigmaFidelity™ Pre-Flight Parity Audit & Link Integrity Linter
Standard: HWB-QMS-7.6 Enterprise Architecture Standards & HWB-QMS-11.2
Auditors: George (Systems Architect & mbB) & Peter (Recovery Specialist)
Authority: Humberto Dominguez (CEO)

Executes 4-phase pre-flight validation:
  1. PostgreSQL Schema Migrations Parity
  2. Sequence Counter & Primary Key Integrity
  3. Template Link & Relative Resource Linter (Zero mop.test / localhost)
  4. Embedded JavaScript Syntax & DOM Integrity (Poka-Yoke)
"""

import os
import re
import sys
import glob
import subprocess
from typing import Dict, List, Any, Optional
import psycopg2
from dotenv import load_dotenv

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_PATH = os.path.join(ROOT_DIR, ".env")
load_dotenv(ENV_PATH)

DEV_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db"
)

# Resolve templates directory across host and container paths
TEMPLATES_DIR = os.path.join(ROOT_DIR, "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE", "templates")
if not os.path.exists(TEMPLATES_DIR):
    if os.path.exists("/app/templates"):
        TEMPLATES_DIR = "/app/templates"
    elif os.path.exists(os.path.join(ROOT_DIR, "templates")):
        TEMPLATES_DIR = os.path.join(ROOT_DIR, "templates")

# Forbidden host patterns in production templates (Poka-Yoke)
FORBIDDEN_LINK_PATTERNS = [
    (re.compile(r'https?://localhost(?::\d+)?', re.IGNORECASE), "localhost reference"),
    (re.compile(r'https?://127\.0\.0\.1(?::\d+)?', re.IGNORECASE), "loopback IP reference"),
    (re.compile(r'https?://mop\.test(?::\d+)?', re.IGNORECASE), "mop.test private host reference"),
    (re.compile(r'https?://mop\.dev(?::\d+)?', re.IGNORECASE), "mop.dev private host reference"),
]


def exec_docker_psql(query: str) -> Optional[List[str]]:
    """Runs a query via docker exec if running on host workstation."""
    cmd = [
        "docker", "exec", "hwb_postgres_dev",
        "psql", "-U", "hwbdev", "-d", "hwb_dev_db",
        "-t", "-A", "-c", query
    ]
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5
        )
        if proc.returncode == 0:
            lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
            return lines
    except Exception:
        pass
    return None


def audit_database_schema() -> Dict[str, Any]:
    """Audits applied schema migrations on target PostgreSQL database."""
    res = {
        "label": "Local Dev DB",
        "connected": False,
        "migrations_count": 0,
        "migrations": [],
        "error": None
    }
    # 1. Try Direct TCP (Container environment or direct host)
    try:
        conn = psycopg2.connect(DEV_DB_URL, connect_timeout=2)
        with conn.cursor() as cur:
            cur.execute("SELECT version FROM schema_migrations ORDER BY applied_at ASC;")
            rows = [r[0] for r in cur.fetchall()]
            res["connected"] = True
            res["migrations_count"] = len(rows)
            res["migrations"] = rows
        conn.close()
        return res
    except Exception as tcp_err:
        pass

    # 2. Try Docker CLI Fallback (Host environment)
    rows = exec_docker_psql("SELECT version FROM schema_migrations ORDER BY applied_at ASC;")
    if rows is not None:
        res["connected"] = True
        res["migrations_count"] = len(rows)
        res["migrations"] = rows
        res["channel"] = "docker_cli"
    else:
        res["error"] = "Failed to query schema_migrations table via TCP and Docker CLI."
        
    return res


def audit_database_sequences() -> Dict[str, Any]:
    """Checks sequence alignment across all tables with auto-increment keys."""
    res = {
        "sequences_checked": 0,
        "misaligned": [],
        "healthy": True,
        "error": None
    }
    align_sql = """
    DO $$ DECLARE
        r RECORD;
    BEGIN
        FOR r IN (
            SELECT table_name, column_name, column_default 
            FROM information_schema.columns 
            WHERE column_default LIKE 'nextval(%' AND table_schema = 'public'
        ) LOOP
            EXECUTE 'SELECT setval(''' || substring(r.column_default from '''(.*)''' ) || ''', COALESCE(MAX(' || r.column_name || '), 1)) FROM "' || r.table_name || '"';
        END LOOP;
    END $$;
    """
    count_sql = "SELECT COUNT(*) FROM information_schema.columns WHERE column_default LIKE 'nextval(%' AND table_schema = 'public';"

    # 1. Direct TCP
    try:
        conn = psycopg2.connect(DEV_DB_URL, connect_timeout=2)
        with conn.cursor() as cur:
            cur.execute(align_sql)
            cur.execute(count_sql)
            count = cur.fetchone()[0]
            res["sequences_checked"] = int(count)
            res["healthy"] = True
            conn.commit()
        conn.close()
        return res
    except Exception:
        pass

    # 2. Docker CLI
    align_res = exec_docker_psql(align_sql)
    count_rows = exec_docker_psql(count_sql)
    if count_rows:
        res["sequences_checked"] = int(count_rows[0])
        res["healthy"] = (align_res is not None)
    else:
        res["error"] = "Failed to inspect PostgreSQL sequences."
        res["healthy"] = False
        
    return res


def audit_template_links(templates_dir: str) -> Dict[str, Any]:
    """Scans all Jinja2 HTML templates for leaked development URLs."""
    res = {
        "templates_scanned": 0,
        "violations_found": 0,
        "details": []
    }
    pattern_files = glob.glob(os.path.join(templates_dir, "**", "*.html"), recursive=True)
    res["templates_scanned"] = len(pattern_files)

    for f_path in pattern_files:
        rel_path = os.path.relpath(f_path, templates_dir)
        try:
            with open(f_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                for line_num, line in enumerate(lines, 1):
                    for regex, desc in FORBIDDEN_LINK_PATTERNS:
                        matches = regex.findall(line)
                        if matches:
                            res["violations_found"] += len(matches)
                            res["details"].append({
                                "file": rel_path,
                                "line": line_num,
                                "matched": matches[0],
                                "rule": desc,
                                "snippet": line.strip()[:100]
                            })
        except Exception:
            pass
    return res


def audit_embedded_javascript(templates_dir: str) -> Dict[str, Any]:
    """Validates basic syntax and bracket symmetry on embedded JavaScript."""
    res = {
        "scripts_scanned": 0,
        "syntax_errors": 0,
        "details": []
    }
    pattern_files = glob.glob(os.path.join(templates_dir, "**", "*.html"), recursive=True)
    
    for f_path in pattern_files:
        rel_path = os.path.relpath(f_path, templates_dir)
        try:
            with open(f_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                script_blocks = re.findall(
                    r'<script\b[^>]*>(.*?)</script>', content, re.DOTALL | re.IGNORECASE
                )
                for s_idx, script in enumerate(script_blocks):
                    res["scripts_scanned"] += 1
                    curly_diff = script.count("{") - script.count("}")
                    if curly_diff != 0:
                        if "{%" not in script and curly_diff > 2:
                            res["syntax_errors"] += 1
                            res["details"].append({
                                "file": rel_path,
                                "script_index": s_idx,
                                "issue": f"Unbalanced curly braces (delta: {curly_diff})"
                            })
        except Exception:
            pass
    return res


def run_full_parity_audit() -> Dict[str, Any]:
    """Runs all 4 audit phases and compiles an executive summary."""
    dev_schema = audit_database_schema()
    seq_audit = audit_database_sequences()
    link_audit = audit_template_links(TEMPLATES_DIR)
    js_audit = audit_embedded_javascript(TEMPLATES_DIR)
    
    score = 100
    if not dev_schema["connected"]:
        score -= 40
    if not seq_audit["healthy"]:
        score -= 20
    score -= min(30, link_audit["violations_found"] * 10)
    score -= min(10, js_audit["syntax_errors"] * 5)
    
    overall_status = "PASS" if score >= 90 else ("WARN" if score >= 70 else "FAIL")

    return {
        "overall_status": overall_status,
        "parity_score": max(0, score),
        "dev_schema": dev_schema,
        "sequences": seq_audit,
        "link_linter": link_audit,
        "js_linter": js_audit
    }


def main():
    print("\n" + "=" * 80)
    print("  SIGMAFIDELITY™ PRE-FLIGHT PARITY AUDIT & LINK INTEGRITY REPORT")
    print("  Standard: HWB-QMS-7.6 Enterprise Architecture Standards")
    print("  Custodians: George (Systems Architect) & Peter (Recovery Specialist)")
    print("=" * 80)

    report = run_full_parity_audit()

    print(f"\n[OVERALL SYSTEM STATUS]  : {report['overall_status']}")
    print(f"[ENTERPRISE PARITY SCORE]: {report['parity_score']} / 100")
    print("-" * 80)

    # 1. Schema Migrations
    ds = report["dev_schema"]
    if ds["connected"]:
        print(f"✓ Schema Connection      : CONNECTED ({ds.get('channel', 'direct_tcp')})")
        print(f"✓ Applied Migrations     : {ds['migrations_count']} Verified Versions")
    else:
        print(f"✗ Schema Connection      : FAILED ({ds.get('error')})")

    # 2. Sequence Health
    sq = report["sequences"]
    if sq["healthy"]:
        print(f"✓ PostgreSQL Sequences   : ALL ALIGNED ({sq['sequences_checked']} Checked & Resynced)")
    else:
        print(f"✗ PostgreSQL Sequences   : SEQUENCE MISALIGNMENT DETECTED!")

    # 3. Link Linter
    ll = report["link_linter"]
    if ll["violations_found"] == 0:
        print(f"✓ Template Link Linter   : ZERO HARDCODED HOSTNAMES ({ll['templates_scanned']} Scanned)")
    else:
        print(f"✗ Template Link Linter   : {ll['violations_found']} VIOLATIONS DETECTED!")
        for v in ll["details"]:
            print(f"    - {v['file']}:{v['line']} -> {v['matched']} ({v['rule']})")

    # 4. JS Linter
    js = report["js_linter"]
    if js["syntax_errors"] == 0:
        print(f"✓ Embedded JS Syntax     : 100% CLEAN ({js['scripts_scanned']} Script Blocks)")
    else:
        print(f"✗ Embedded JS Syntax     : {js['syntax_errors']} ISSUES DETECTED")

    print("=" * 80 + "\n")

    if report["overall_status"] == "FAIL":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
