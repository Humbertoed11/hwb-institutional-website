#!/usr/bin/env python3
"""Peter Recovery Sentinel v2.0.0 for HWB Cleaning Services LLC.

Provides the unified 3-command local recovery workflow strictly scoped to
/home/humbertoed/gemini_projects per HWB-QMS-9.3 v4.5.0 and HWB-QMS-9.2 v4.4.0:
  1. checkpoint --label <name>
  2. rollback --label <name> [--code-only | --full]
  3. verify (default when no subcommand is supplied)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv

VERSION: str = "2.0.0"
PROJECT_ROOT: Path = Path("/home/humbertoed/gemini_projects").resolve()
LATEST_DUMP: Path = PROJECT_ROOT / "backups" / "latest" / "hwb_dev_db.dump"
LATEST_SHA: Path = (
    PROJECT_ROOT / "backups" / "latest" / "hwb_dev_db.dump.sha256"
)
CHECKPOINTS_ROOT: Path = PROJECT_ROOT / "backups" / "checkpoints"

PG_CONTAINER: str = "hwb_postgres_dev"
WEB_CONTAINER: str = "hwb_web_app"
WORKER_CONTAINER: str = "hwb_agent_worker"
PG_USER: str = "hwbdev"
PG_PASSWORD: str = "hwbpassword"
PG_DB: str = "hwb_dev_db"
VERIFY_TMP_DB: str = "hwb_peter_verify_tmp"
RESTORE_STAGE_DB: str = "hwb_restore_stage"
SWAP_OLD_DB: str = "hwb_dev_db_prev_swap"

MIN_PUBLIC_TABLES: int = 80
MAX_BACKUP_AGE_MINUTES: float = 90.0
EXPECTED_WORKER_DAEMONS: tuple[str, ...] = (
    "sigma_orchestrator.py",
    "watchdog.py",
    "telegram_listener.py",
    "tessa_regression_suite.py",
)
LABEL_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z0-9._-]+$")


def validate_label(label: str) -> str:
    """Validate checkpoint label to block path traversal or unsafe names."""
    cleaned = label.strip()
    if not cleaned or not LABEL_PATTERN.fullmatch(cleaned):
        raise ValueError(
            f"Invalid label '{label}'. Use letters, numbers, '.', '_', or '-'."
        )
    if cleaned in {".", ".."}:
        raise ValueError("Checkpoint label cannot be '.' or '..'.")
    return cleaned


def compute_sha256(file_path: Path) -> str:
    """Compute hex SHA-256 digest of a file in 1 MB chunks."""
    hasher = hashlib.sha256()
    with file_path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def run_cmd(
    args: list[str],
    *,
    cwd: Path | None = None,
    stdin_file: Path | None = None,
    stdout_file: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Execute a subprocess command with explicit stream handling."""
    in_handle = stdin_file.open("rb") if stdin_file is not None else None
    out_handle = stdout_file.open("wb") if stdout_file is not None else None
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd) if cwd is not None else None,
            stdin=in_handle,
            stdout=out_handle if out_handle is not None else subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=out_handle is None,
            check=False,
        )
    finally:
        if in_handle is not None:
            in_handle.close()
        if out_handle is not None:
            out_handle.close()

    if check and result.returncode != 0:
        err_text = (result.stderr or "").strip()
        if isinstance(result.stderr, bytes):
            err_text = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"Command failed (exit {result.returncode}): "
            f"{' '.join(args)} | {err_text}"
        )
    return result


def get_pg_connection() -> Any:
    """Open a PostgreSQL connection to hwb_dev_db from host or container."""
    in_docker = Path("/.dockerenv").exists()
    host = "db" if in_docker else "127.0.0.1"
    port = int(os.environ.get("PGPORT", "5432"))
    user = os.environ.get("POSTGRES_USER", PG_USER)
    password = os.environ.get("POSTGRES_PASSWORD", PG_PASSWORD)
    return psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=PG_DB,
        connect_timeout=5,
    )


def record_peter_audit(
    action: str,
    healthy: bool,
    details: dict[str, Any],
) -> None:
    """Record Peter status in AIEmployeeHeartbeat and SecurityAuditLogs."""
    status_label = "ONLINE" if healthy else "DEGRADED"
    severity = "INFO" if healthy else "CRITICAL"
    status_code = 200 if healthy else 500
    payload_json = json.dumps(details, sort_keys=True)

    conn = get_pg_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO "AIEmployeeHeartbeat" (
                        worker_name,
                        status,
                        last_pulse_at,
                        tasks_completed,
                        telemetry_json
                    )
                    VALUES (%s, %s, NOW(), 1, %s::jsonb)
                    ON CONFLICT (worker_name) DO UPDATE SET
                        status = EXCLUDED.status,
                        last_pulse_at = NOW(),
                        tasks_completed = COALESCE(
                            "AIEmployeeHeartbeat".tasks_completed, 0
                        ) + 1,
                        telemetry_json = EXCLUDED.telemetry_json
                    """,
                    ("peter_recovery_sentinel", status_label, payload_json),
                )
                cur.execute(
                    """
                    INSERT INTO "SecurityAuditLogs" (
                        event_category,
                        event_action,
                        username,
                        user_role,
                        ip_address,
                        user_agent,
                        endpoint,
                        http_method,
                        status_code,
                        severity,
                        details
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
                    )
                    """,
                    (
                        "DISASTER_RECOVERY",
                        action,
                        "peter_sentinel",
                        "RECOVERY_SPECIALIST",
                        "127.0.0.1",
                        f"PeterSentinel/{VERSION}",
                        f"/cli/peter_sentinel/{action.lower()}",
                        "CLI",
                        status_code,
                        severity,
                        payload_json,
                    ),
                )
    finally:
        conn.close()


def run_psql_maintenance(sql: str, database: str = "postgres") -> str:
    """Execute administrative SQL inside hwb_postgres_dev via docker exec."""
    res = run_cmd(
        [
            "docker",
            "exec",
            PG_CONTAINER,
            "psql",
            "-U",
            PG_USER,
            "-d",
            database,
            "-t",
            "-A",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            sql,
        ]
    )
    return (res.stdout or "").strip()


def verify_dump_via_temp_db(dump_path: Path, temp_db: str) -> int:
    """Restore dump into an isolated database and return public table count."""
    run_psql_maintenance(
        f"DROP DATABASE IF EXISTS {temp_db} WITH (FORCE);"
    )
    run_psql_maintenance(f"CREATE DATABASE {temp_db};")
    run_cmd(
        [
            "docker",
            "exec",
            "-i",
            PG_CONTAINER,
            "pg_restore",
            "-U",
            PG_USER,
            "-d",
            temp_db,
            "--no-owner",
            "--exit-on-error",
        ],
        stdin_file=dump_path,
    )
    count_str = run_psql_maintenance(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE';",
        database=temp_db,
    )
    table_count = int(count_str.strip() or "0")
    if table_count < MIN_PUBLIC_TABLES:
        raise RuntimeError(
            f"Restored database {temp_db} has only {table_count} public "
            f"tables (minimum {MIN_PUBLIC_TABLES} expected)."
        )
    return table_count


def build_code_bundle(bundle_path: Path) -> None:
    """Archive active HWB code, QMS, scripts, and config with chmod 600."""
    targets = [
        "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE",
        "HWB-COMPANY/HWB-QMS",
        "scripts",
        "GEMINI.md",
        "HWB-SESSION-RECOVERY.md",
        "docker-compose.yml",
    ]
    existing_targets = [
        rel for rel in targets if (PROJECT_ROOT / rel).exists()
    ]
    tar_args = [
        "tar",
        "-czf",
        str(bundle_path),
        "--exclude=HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/gen_ai_staging",
        "--exclude=HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/backups",
        "--exclude=HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/backup",
        "--exclude=__pycache__",
        "--exclude=.pytest_cache",
        "--exclude=node_modules",
        *existing_targets,
    ]
    run_cmd(tar_args, cwd=PROJECT_ROOT)
    os.chmod(bundle_path, 0o600)
    if bundle_path.stat().st_size == 0:
        raise RuntimeError(f"Code archive is empty: {bundle_path}")


def cmd_checkpoint(label: str) -> int:
    """Create a pinned, verified local checkpoint immune to 24h auto-purge."""
    safe_label = validate_label(label)
    vault_dir = CHECKPOINTS_ROOT / safe_label
    CHECKPOINTS_ROOT.mkdir(parents=True, exist_ok=True)
    vault_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(vault_dir, 0o700)

    print(
        f"=== [Peter v{VERSION}] Creating Checkpoint '{safe_label}' "
        f"in {vault_dir} ==="
    )

    dump_file = vault_dir / "hwb_dev_db.dump"
    env_src = PROJECT_ROOT / ".env"
    web_env_src = (
        PROJECT_ROOT / "HWB-COMPANY" / "HWB-IT" / "HWB-IT-WEBSITE" / ".env"
    )
    bundle_file = vault_dir / "hwb_code_bundle.tar.gz"
    sha_file = vault_dir / "SHA256SUMS.txt"
    manifest_file = vault_dir / "manifest.json"

    # 1. Capture compressed PostgreSQL 16.15 custom-format dump
    print("[1/4] Capturing PostgreSQL 16.15 custom dump (chmod 600)...")
    run_cmd(
        [
            "docker",
            "exec",
            PG_CONTAINER,
            "pg_dump",
            "-U",
            PG_USER,
            "-F",
            "c",
            PG_DB,
        ],
        stdout_file=dump_file,
    )
    os.chmod(dump_file, 0o600)
    if dump_file.stat().st_size == 0:
        raise RuntimeError(f"Database dump is empty: {dump_file}")

    # 2. Freeze .env files with chmod 600
    print("[2/4] Freezing .env secret configuration (chmod 600)...")
    tracked_files: list[Path] = [dump_file]
    if env_src.exists():
        env_dest = vault_dir / ".env"
        shutil.copy2(env_src, env_dest)
        os.chmod(env_dest, 0o600)
        tracked_files.append(env_dest)
    if web_env_src.exists():
        web_env_dest = vault_dir / "website.env"
        shutil.copy2(web_env_src, web_env_dest)
        os.chmod(web_env_dest, 0o600)
        tracked_files.append(web_env_dest)

    # 3. Archive active HWB code, QMS, and scripts
    print("[3/4] Archiving HWB code, QMS, and scripts (chmod 600)...")
    build_code_bundle(bundle_file)
    tracked_files.append(bundle_file)

    # 4. Write SHA256SUMS.txt and verify upfront via temporary database restore
    checksum_lines: list[str] = []
    artifact_hashes: dict[str, str] = {}
    for item in tracked_files:
        digest = compute_sha256(item)
        artifact_hashes[item.name] = digest
        checksum_lines.append(f"{digest}  {item.name}")
    sha_file.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    os.chmod(sha_file, 0o600)

    print(
        f"[4/4] Test-restoring dump into temporary DB '{VERIFY_TMP_DB}'..."
    )
    verified_tables = 0
    try:
        verified_tables = verify_dump_via_temp_db(dump_file, VERIFY_TMP_DB)
    finally:
        try:
            run_psql_maintenance(
                f"DROP DATABASE IF EXISTS {VERIFY_TMP_DB} WITH (FORCE);"
            )
        except Exception as cleanup_err:
            print(
                f"[WARN] Temp DB cleanup warning: {cleanup_err}",
                file=sys.stderr,
            )

    created_iso = datetime.now(timezone.utc).isoformat()
    manifest_data: dict[str, Any] = {
        "version": VERSION,
        "label": safe_label,
        "created_at_utc": created_iso,
        "project_root": str(PROJECT_ROOT),
        "dump_size_bytes": dump_file.stat().st_size,
        "code_bundle_size_bytes": bundle_file.stat().st_size,
        "verified_public_tables": verified_tables,
        "sha256": artifact_hashes,
    }
    manifest_file.write_text(
        json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8"
    )
    os.chmod(manifest_file, 0o600)

    record_peter_audit("PETER_CHECKPOINT", True, manifest_data)
    print(
        f"[OK] Checkpoint '{safe_label}' pinned & restore-verified "
        f"({verified_tables} public tables, dump "
        f"{dump_file.stat().st_size // (1024 * 1024)}MB, "
        f"code {bundle_file.stat().st_size // (1024 * 1024)}MB)."
    )
    return 0


def verify_checkpoint_checksums(vault_dir: Path) -> None:
    """Verify every artifact listed in SHA256SUMS.txt before rollback."""
    sha_file = vault_dir / "SHA256SUMS.txt"
    if not sha_file.is_file():
        raise FileNotFoundError(f"Missing checksum manifest: {sha_file}")

    lines = [
        ln.strip()
        for ln in sha_file.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    if not lines:
        raise RuntimeError(f"Empty checksum manifest: {sha_file}")

    for line in lines:
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise RuntimeError(f"Malformed SHA256SUMS entry: {line}")
        expected_sha, rel_name = parts[0], parts[1].strip()
        target = vault_dir / rel_name
        if not target.is_file():
            raise FileNotFoundError(f"Missing checkpoint artifact: {target}")
        actual_sha = compute_sha256(target)
        if actual_sha != expected_sha:
            raise RuntimeError(
                f"SHA-256 mismatch for {rel_name}: "
                f"expected {expected_sha}, got {actual_sha}"
            )


def wait_for_web_and_workers(check_workers: bool) -> dict[str, Any]:
    """Wait for web HTTP 200 and all 4 supervised worker daemons."""
    web_ok = False
    for _ in range(20):
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:5000/heartbeat", method="GET"
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    web_ok = True
                    break
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(1.0)

    if not web_ok:
        raise RuntimeError(
            "Web container http://127.0.0.1:5000/heartbeat did not return 200."
        )

    matched_daemons: list[str] = []
    if check_workers:
        for _ in range(15):
            top_res = run_cmd(["docker", "top", WORKER_CONTAINER])
            top_out = top_res.stdout or ""
            matched_daemons = [
                d for d in EXPECTED_WORKER_DAEMONS if d in top_out
            ]
            if len(matched_daemons) == len(EXPECTED_WORKER_DAEMONS):
                break
            time.sleep(1.0)
        if len(matched_daemons) != len(EXPECTED_WORKER_DAEMONS):
            raise RuntimeError(
                f"Worker verification incomplete ({len(matched_daemons)}/"
                f"{len(EXPECTED_WORKER_DAEMONS)}): {matched_daemons}"
            )

    return {
        "web_heartbeat_200": web_ok,
        "verified_workers": matched_daemons,
    }


def cmd_rollback(label: str, full_restore: bool) -> int:
    """Restore code-only or full code + staging-swapped PG16 database."""
    safe_label = validate_label(label)
    vault_dir = CHECKPOINTS_ROOT / safe_label
    if not vault_dir.is_dir():
        raise FileNotFoundError(f"Checkpoint '{safe_label}' not found.")

    mode_name = "FULL" if full_restore else "CODE_ONLY"
    print(
        f"=== [Peter v{VERSION}] Executing {mode_name} Rollback from "
        f"Checkpoint '{safe_label}' ==="
    )
    verify_checkpoint_checksums(vault_dir)
    print("[OK] Checkpoint SHA256SUMS.txt verified.")

    bundle_file = vault_dir / "hwb_code_bundle.tar.gz"
    dump_file = vault_dir / "hwb_dev_db.dump"

    if not full_restore:
        run_cmd(
            ["tar", "-xzf", str(bundle_file), "-C", str(PROJECT_ROOT)]
        )
        run_cmd(["docker", "restart", WEB_CONTAINER])
        health = wait_for_web_and_workers(check_workers=False)
        details: dict[str, Any] = {
            "version": VERSION,
            "label": safe_label,
            "mode": "code-only",
            **health,
        }
        record_peter_audit("PETER_ROLLBACK_CODE", True, details)
        print(
            f"[OK] Code-only rollback '{safe_label}' completed & "
            f"{WEB_CONTAINER} verified HTTP 200."
        )
        return 0

    # Full rollback: stage PG16 restore into hwb_restore_stage first
    print(
        f"[1/4] Restoring pinned PG16 dump into clean staging DB "
        f"'{RESTORE_STAGE_DB}'..."
    )
    staged_tables = 0
    try:
        staged_tables = verify_dump_via_temp_db(dump_file, RESTORE_STAGE_DB)
    except Exception:
        try:
            run_psql_maintenance(
                f"DROP DATABASE IF EXISTS {RESTORE_STAGE_DB} WITH (FORCE);"
            )
        except Exception as cleanup_err:
            print(
                f"[WARN] Staging cleanup warning: {cleanup_err}",
                file=sys.stderr,
            )
        raise

    print(
        f"[2/4] Extracting code bundle and .env files "
        f"({staged_tables} staged tables ready)..."
    )
    run_cmd(["tar", "-xzf", str(bundle_file), "-C", str(PROJECT_ROOT)])
    env_vault = vault_dir / ".env"
    if env_vault.exists():
        env_target = PROJECT_ROOT / ".env"
        shutil.copy2(env_vault, env_target)
        os.chmod(env_target, 0o600)
    web_env_vault = vault_dir / "website.env"
    if web_env_vault.exists():
        web_env_target = (
            PROJECT_ROOT / "HWB-COMPANY" / "HWB-IT" / "HWB-IT-WEBSITE" / ".env"
        )
        shutil.copy2(web_env_vault, web_env_target)
        os.chmod(web_env_target, 0o600)

    print(
        f"[3/4] Stopping {WEB_CONTAINER} & {WORKER_CONTAINER} for clean "
        f"database swap..."
    )
    run_cmd(["docker", "stop", WEB_CONTAINER, WORKER_CONTAINER])
    try:
        run_psql_maintenance(
            f"DROP DATABASE IF EXISTS {SWAP_OLD_DB} WITH (FORCE);"
        )
        run_psql_maintenance(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname IN ('{PG_DB}', '{RESTORE_STAGE_DB}') "
            "AND pid <> pg_backend_pid();"
        )
        run_psql_maintenance(
            f"ALTER DATABASE {PG_DB} RENAME TO {SWAP_OLD_DB};"
        )
        run_psql_maintenance(
            f"ALTER DATABASE {RESTORE_STAGE_DB} RENAME TO {PG_DB};"
        )
        run_psql_maintenance(
            f"DROP DATABASE IF EXISTS {SWAP_OLD_DB} WITH (FORCE);"
        )
    finally:
        print(f"[4/4] Restarting {WEB_CONTAINER} & {WORKER_CONTAINER}...")
        run_cmd(["docker", "start", WEB_CONTAINER, WORKER_CONTAINER])

    health = wait_for_web_and_workers(check_workers=True)
    full_details: dict[str, Any] = {
        "version": VERSION,
        "label": safe_label,
        "mode": "full",
        "restored_public_tables": staged_tables,
        **health,
    }
    record_peter_audit("PETER_ROLLBACK_FULL", True, full_details)
    print(
        f"[OK] Full rollback '{safe_label}' completed ({staged_tables} "
        f"tables, 4/4 worker daemons active, HTTP 200)."
    )
    return 0


def cmd_verify() -> int:
    """Verify latest hourly dump age (<90m), size, chmod 600, and SHA-256."""
    print(f"=== [Peter v{VERSION}] Verifying HWB Backup Health ===")
    issues: list[str] = []
    age_minutes: float = -1.0
    size_bytes: int = 0
    dump_mode_oct: str = "missing"
    sha_mode_oct: str = "missing"
    sha_matched: bool = False
    actual_sha: str = ""

    if not LATEST_DUMP.is_file():
        issues.append(f"Missing latest dump: {LATEST_DUMP}")
    else:
        st = LATEST_DUMP.stat()
        size_bytes = st.st_size
        age_minutes = round((time.time() - st.st_mtime) / 60.0, 2)
        mode_bits = stat.S_IMODE(st.st_mode)
        dump_mode_oct = f"0{mode_bits:o}"
        if size_bytes <= 0:
            issues.append("Latest dump file is empty (0 bytes).")
        if age_minutes >= MAX_BACKUP_AGE_MINUTES:
            issues.append(
                f"Latest dump age {age_minutes}m exceeds "
                f"{MAX_BACKUP_AGE_MINUTES}m limit."
            )
        if mode_bits != 0o600:
            issues.append(
                f"Latest dump permissions are {dump_mode_oct} "
                "(expected 0600)."
            )

    if not LATEST_SHA.is_file():
        issues.append(f"Missing SHA-256 file: {LATEST_SHA}")
    else:
        sha_st = LATEST_SHA.stat()
        sha_bits = stat.S_IMODE(sha_st.st_mode)
        sha_mode_oct = f"0{sha_bits:o}"
        if sha_bits != 0o600:
            issues.append(
                f"SHA-256 file permissions are {sha_mode_oct} "
                "(expected 0600)."
            )
        raw_text = LATEST_SHA.read_text(encoding="utf-8").strip()
        expected_sha = raw_text.split()[0] if raw_text else ""
        if LATEST_DUMP.is_file() and expected_sha:
            actual_sha = compute_sha256(LATEST_DUMP)
            if actual_sha == expected_sha:
                sha_matched = True
            else:
                issues.append(
                    f"SHA-256 mismatch (expected {expected_sha[:16]}..., "
                    f"got {actual_sha[:16]}...)."
                )
        else:
            issues.append("SHA-256 checksum file is empty or unreadable.")

    checkpoint_labels: list[str] = []
    if CHECKPOINTS_ROOT.is_dir():
        checkpoint_labels = sorted(
            p.name for p in CHECKPOINTS_ROOT.iterdir() if p.is_dir()
        )

    healthy = len(issues) == 0
    report: dict[str, Any] = {
        "version": VERSION,
        "healthy": healthy,
        "latest_dump": str(LATEST_DUMP),
        "age_minutes": age_minutes,
        "size_bytes": size_bytes,
        "dump_permissions": dump_mode_oct,
        "sha_permissions": sha_mode_oct,
        "sha256_verified": sha_matched,
        "sha256_prefix": actual_sha[:16] if actual_sha else "",
        "pinned_checkpoints": checkpoint_labels,
        "issues": issues,
    }

    try:
        record_peter_audit("PETER_VERIFY", healthy, report)
    except Exception as db_err:
        issues.append(f"PostgreSQL audit write failed: {db_err}")
        healthy = False

    if not healthy:
        for msg in issues:
            print(f"[FAIL] {msg}", file=sys.stderr)
        return 1

    print(
        f"[OK] Latest dump verified: {LATEST_DUMP.name} | "
        f"size={size_bytes // (1024 * 1024)}MB | age={age_minutes}m (<90m) | "
        f"mode={dump_mode_oct} | sha256={actual_sha[:16]}... | "
        f"checkpoints={len(checkpoint_labels)} | DB heartbeat logged."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build command-line argument parser for Peter Sentinel v2.0.0."""
    parser = argparse.ArgumentParser(
        prog="peter_sentinel.py",
        description=(
            "Peter Recovery Sentinel v2.0.0 — Unified 3-Command Local "
            "Recovery Standard for HWB Cleaning "
            "(/home/humbertoed/gemini_projects)."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    cp_parser = subparsers.add_parser(
        "checkpoint",
        help=(
            "Pin chmod 600 PG16 dump, .env, and code bundle with temp verify."
        ),
    )
    cp_parser.add_argument(
        "--label",
        required=True,
        help="Unique checkpoint label (letters, digits, '.', '_', '-').",
    )

    rb_parser = subparsers.add_parser(
        "rollback",
        help="Restore code-only or full code + clean staging-swapped PG16 DB.",
    )
    rb_parser.add_argument(
        "--label",
        required=True,
        help="Pinned checkpoint label in backups/checkpoints/<label>/.",
    )
    mode_group = rb_parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--code-only",
        action="store_true",
        help="Restore active code/QMS archive and restart hwb_web_app.",
    )
    mode_group.add_argument(
        "--full",
        action="store_true",
        help="Restore code, .env, and PG16 DB via hwb_restore_stage swap.",
    )

    subparsers.add_parser(
        "verify",
        help="Verify backups/latest/hwb_dev_db.dump (<90m, 0600, SHA-256).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for Peter Recovery Sentinel v2.0.0."""
    load_dotenv(PROJECT_ROOT / ".env")
    args_list = list(sys.argv[1:] if argv is None else argv)
    if not args_list:
        args_list = ["verify"]

    parser = build_parser()
    parsed = parser.parse_args(args_list)

    try:
        if parsed.command == "checkpoint":
            return cmd_checkpoint(parsed.label)
        if parsed.command == "rollback":
            return cmd_rollback(parsed.label, full_restore=bool(parsed.full))
        return cmd_verify()
    except Exception as exc:
        print(f"[SENTINEL CRITICAL FAILURE] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
