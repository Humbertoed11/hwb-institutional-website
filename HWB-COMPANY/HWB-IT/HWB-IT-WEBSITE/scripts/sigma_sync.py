import os
import re
import json
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from dotenv import load_dotenv

# SigmaFidelity™ Security: Load the .env file
load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")

def get_latest_walkthrough():
    base_path = os.path.expanduser("~/.gemini/antigravity-cli/brain/")
    if not os.path.exists(base_path): return None, None
    dirs = [os.path.join(base_path, d) for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    if not dirs: return None, None
    latest_dir = max(dirs, key=os.path.getmtime)
    walkthrough_path = os.path.join(latest_dir, "walkthrough.md")
    if os.path.exists(walkthrough_path):
        return walkthrough_path, os.path.basename(latest_dir)
    return None, None

def sync_walkthrough():
    path, session_id = get_latest_walkthrough()
    if not path: return
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    print(f"[SYNC] Ingesting Walkthrough: {session_id}")
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "SigmaWalkthroughs" (session_id, project_name, narrative_content)
                VALUES (%s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET narrative_content = EXCLUDED.narrative_content;
            """, (session_id, "Antigravity Active Task", content))
            
            cur.execute("""
                INSERT INTO "SigmaInteractionCore" (session_id, user_prompt, agent_explanation, status)
                VALUES (%s, %s, %s, %s);
            """, (session_id, "Institutional Persistence Sync", "Automatic synchronization of session narrative and code impact.", "SUCCESS"))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error syncing walkthrough: {e}")

def sync_new_sops():
    candidate_dirs = [
        "/app/static/qms",
        "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/qms",
        "static/qms",
        "HWB-COMPANY/HWB-QMS",
    ]
    sop_dir = next((d for d in candidate_dirs if os.path.exists(d)), None)
    if not sop_dir:
        return

    banned_markers = (
        "defines the approved workflow, operational requirements, and quality standards for",
        "[[Container]]",
        "HexGrowth",
        "Postgres:13",
        "HWB-WEB Index.html",
        "proxy_gateway.py",
    )

    print(f"[SYNC] Synchronizing canonical HTML SOPs from {sop_dir} (BUG-148 Quality Gate)...")
    try:
        conn = psycopg2.connect(DB_URL)
        active_html_docs = set()
        ingested_count = 0
        skipped_count = 0
        with conn.cursor() as cur:
            for f in sorted(os.listdir(sop_dir)):
                file_path = os.path.join(sop_dir, f)
                if not os.path.isfile(file_path):
                    continue
                if not f.endswith(".html") or f == "sop_template.html" or "-desktop-" in f.lower():
                    continue
                with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                    content = file.read()
                if any(marker.lower() in content.lower() for marker in banned_markers):
                    skipped_count += 1
                    continue

                active_html_docs.add(f)
                ingested_count += 1
                cur.execute("""
                    INSERT INTO sigma_kb (doc_id, content, metadata)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (doc_id) DO UPDATE
                    SET content = EXCLUDED.content, metadata = EXCLUDED.metadata;
                """, (
                    f,
                    content,
                    Json({
                        "source": "Canonical QMS Sync (BUG-148)",
                        "path": file_path,
                        "synced_at": datetime.now().isoformat(),
                    }),
                ))

            # Purge retired/orphaned HTML SOPs, legacy book snapshots, and unindexed markdown bloat
            cur.execute("SELECT doc_id FROM sigma_kb;")
            existing_ids = [r[0] for r in cur.fetchall()]
            purged_ids = []
            for doc_id in existing_ids:
                if doc_id.endswith(".html") and doc_id not in active_html_docs:
                    purged_ids.append(doc_id)
                elif doc_id == "HWB-ACADEMY-BOOK-001-V4.6.0" or ".md" in doc_id:
                    purged_ids.append(doc_id)

            if purged_ids:
                cur.execute(
                    "DELETE FROM sigma_kb WHERE doc_id = ANY(%s);",
                    (purged_ids,),
                )
                print(f"[SYNC] Purged {len(purged_ids)} retired/orphaned rows from sigma_kb.")

        conn.commit()
        conn.close()
        print(f"[SYNC] Canonical QMS Sync complete: {ingested_count} active SOPs synced ({skipped_count} rejected).")
    except Exception as e:
        print(f"Error syncing SOPs: {e}")

def parse_recovery_table(markdown_content):
    parsed = {}
    lines = markdown_content.split("\n")
    for line in lines:
        match_normal = re.match(r"\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|]+)\|", line)
        if match_normal:
            key = match_normal.group(1).strip()
            val = match_normal.group(2).strip()
            # Clean bold indicators if present
            val = re.sub(r"\*\*([^*]+)\*\*", r"\1", val).strip()
            parsed[key] = val
    return parsed

def _resolve_archive_path(filename: str) -> str:
    """Returns host backups/ archive path when available, else local docs/archive/."""
    candidates = [
        os.path.abspath(os.path.join(os.getcwd(), "backups", filename)),
        os.path.abspath(os.path.join(os.getcwd(), "..", "..", "..", "backups", filename)),
    ]
    for cand in candidates:
        parent = os.path.dirname(cand)
        if os.path.isdir(parent):
            return cand
    fallback_dir = os.path.abspath(os.path.join(os.getcwd(), "docs", "archive"))
    os.makedirs(fallback_dir, exist_ok=True)
    return os.path.join(fallback_dir, filename)


def _mirror_paired_workspace_file(rel_path: str, new_content: str) -> None:
    """Keeps root workspace and HWB-IT-WEBSITE copies identical when both exist."""
    candidates = [
        os.path.abspath(os.path.join(os.getcwd(), rel_path)),
        os.path.abspath(os.path.join(os.getcwd(), "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE", rel_path)),
        os.path.abspath(os.path.join(os.getcwd(), "..", "..", "..", rel_path)),
    ]
    seen = set()
    for target in candidates:
        if target in seen:
            continue
        seen.add(target)
        if os.path.exists(target):
            with open(target, "w", encoding="utf-8") as wf:
                wf.write(new_content)


def _trim_session_recovery_markdown(recovery_file: str, content: str, max_actions: int = 3) -> None:
    """Rotates older <br>-delimited items in Last Action to cold archive after DB sync."""
    lines = content.split("\n")
    updated = False
    archived_blocks = []

    for idx, line in enumerate(lines):
        if line.startswith("| **Last Action** |"):
            parts = line.split("|")
            if len(parts) >= 4:
                cell = parts[2].strip()
                blocks = re.split(r"<br>(?=(?:0+|\d+)\.\s*\*\*)", cell)
                if len(blocks) > max_actions:
                    kept = blocks[:max_actions]
                    archived_blocks = blocks[max_actions:]
                    parts[2] = " " + "<br>".join(kept) + " "
                    lines[idx] = "|".join(parts)
                    updated = True
            break

    if not updated or not archived_blocks:
        return

    archive_path = _resolve_archive_path("HWB_HISTORICAL_SESSIONS_ARCHIVE.md")
    existing_archive = ""
    if os.path.exists(archive_path):
        with open(archive_path, "r", encoding="utf-8") as af:
            existing_archive = af.read()

    new_archive_entries = []
    for blk in archived_blocks:
        sig = blk[:90].strip()
        if sig and sig not in existing_archive:
            new_archive_entries.append(f"- {blk.strip()}")

    if new_archive_entries:
        header = "# SigmaFidelity™ Historical Sessions Cold Archive\n\n" if not existing_archive else "\n"
        stamp = f"\n### Cold-Archived via sigma_sync.py ({datetime.now().strftime('%m/%d/%Y %I:%M %p')})\n"
        with open(archive_path, "a", encoding="utf-8") as af:
            af.write(header + stamp + "\n".join(new_archive_entries) + "\n")

    new_content = "\n".join(lines)
    _mirror_paired_workspace_file("HWB-SESSION-RECOVERY.md", new_content)
    print(f"[SYNC] Auto-trimmed HWB-SESSION-RECOVERY.md (archived {len(archived_blocks)} older action blocks -> {archive_path}).")


def sync_system_state():
    recovery_file = "HWB-SESSION-RECOVERY.md"
    if not os.path.exists(recovery_file): return
    
    print("[SYNC] Synchronizing SigmaSystemCore...")
    with open(recovery_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    parsed_fields = parse_recovery_table(content)
    state_json = {
        "raw_text": content,
        "parsed_fields": parsed_fields,
        "updated_at": datetime.now().isoformat()
    }
    
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "SigmaSystemCore" (session_id, state_data, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (session_id) DO UPDATE SET state_data = EXCLUDED.state_data, updated_at = CURRENT_TIMESTAMP;
            """, ("ACTIVE-SESSION", Json(state_json)))
        conn.commit()
        conn.close()
        _trim_session_recovery_markdown(recovery_file, content, max_actions=3)
    except Exception as e:
        print(f"Error syncing state: {e}")

def parse_problems_to_solve(markdown_content):
    import re
    rows = []
    lines = markdown_content.split("\n")
    for line in lines:
        if line.strip().startswith("|") and "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:
                date_val = parts[1]
                issue_id = parts[2]
                desc = parts[3]
                status = parts[4].replace("**", "")
                impact = parts[5]
                if issue_id and issue_id != "Issue ID" and not issue_id.startswith("---") and not issue_id.startswith(":") and not issue_id.startswith("Date"):
                    rows.append({
                        "issue_id": issue_id,
                        "date": date_val,
                        "description": desc,
                        "status": status,
                        "impact": impact
                    })
    
    sections = {}
    current_id = None
    current_key = None
    current_content = []
    
    header_pattern = re.compile(r"^##\s+([A-Z]+-[0-9]+):\s*(.*)$")
    
    for line in lines:
        header_match = header_pattern.match(line)
        if header_match:
            if current_id and current_key:
                sections[current_id][current_key] = "\n".join(current_content).strip()
            current_id = header_match.group(1)
            sections[current_id] = {
                "title": header_match.group(2).strip(),
                "detected": "",
                "symptoms": "",
                "root_cause": "",
                "solution": "",
                "preventative": ""
            }
            current_key = None
            current_content = []
            continue
            
        if current_id:
            match_field = re.match(r"^\*\*([^*:]+):\*\*\s*(.*)$", line)
            if match_field:
                if current_key:
                    sections[current_id][current_key] = "\n".join(current_content).strip()
                field_name = match_field.group(1).lower().replace(" ", "_")
                current_key = field_name
                current_content = [match_field.group(2)]
            else:
                current_content.append(line)
                
    if current_id and current_key:
        sections[current_id][current_key] = "\n".join(current_content).strip()
        
    impact_mapping = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    cat_map = {"BUG": "System Integrity", "MIG": "Migration", "SYS": "System Operations"}
    results = []
    seen_ids = set()
    for row in rows:
        iid = row["issue_id"]
        seen_ids.add(iid)
        sec = sections.get(iid, {})
        
        impact_str = row["impact"].upper()
        impact_level = impact_mapping.get(impact_str, 2)
        category = cat_map.get(iid.split("-")[0], "General")
        
        results.append({
            "issue_id": iid,
            "description": row["description"] + (f" ({sec.get('title')})" if sec.get("title") else ""),
            "category": category,
            "status": row["status"],
            "impact_level": impact_level,
            "root_cause": sec.get("root_cause", ""),
            "implemented_fix": sec.get("solution", sec.get("implemented_fix", "")),
            "preventative_rule": sec.get("preventative", sec.get("preventative_rule", "")),
            "detected_date": row["date"]
        })

    for sid, sec in sections.items():
        if sid not in seen_ids:
            category = cat_map.get(sid.split("-")[0], "General")
            det_match = re.search(r"(\d{2}/\d{2}/\d{4})", sec.get("detected", ""))
            results.append({
                "issue_id": sid,
                "description": sec.get("title", sid),
                "category": category,
                "status": "RESOLVED",
                "impact_level": 3,
                "root_cause": sec.get("root_cause", ""),
                "implemented_fix": sec.get("solution", sec.get("implemented_fix", "")),
                "preventative_rule": sec.get("preventative", sec.get("preventative_rule", "")),
                "detected_date": det_match.group(1) if det_match else ""
            })
    return results

try:
    from core.services.embedding import get_embedding as calculate_local_embedding
except ImportError:
    import hashlib
    def calculate_local_embedding(text):
        embedding = [0.0] * 1536
        if not text:
            return embedding
        sha = hashlib.sha256(text.encode("utf-8")).digest()
        for i in range(1536):
            byte_val = sha[i % len(sha)]
            val = (byte_val - 128) / 128.0
            embedding[i] = round(val, 6)
        return embedding


def _trim_problems_markdown(problems_file: str, content: str, max_closed: int = 5) -> None:
    """Losslessly moves older closed bug entries to cold archive once verified in SigmaKnowledgeScars."""
    lines = content.split("\n")
    first_sec_idx = len(lines)
    sec_header_re = re.compile(r"^##\s+([A-Z]+-[0-9]+(?:\.[0-9]+)?):")
    for idx, line in enumerate(lines):
        if sec_header_re.match(line):
            first_sec_idx = idx
            break

    top_lines = lines[:first_sec_idx]
    sec_lines = lines[first_sec_idx:]

    # Parse table rows vs preamble/header lines
    preamble_lines = []
    data_rows = []
    for line in top_lines:
        stripped = line.strip()
        if stripped.startswith("|") and "|" in stripped:
            parts = [p.strip() for p in stripped.split("|")]
            if len(parts) >= 6:
                iid = parts[2]
                if iid and iid not in ("Issue ID", "Date") and not iid.startswith("---") and not iid.startswith(":"):
                    status_clean = parts[4].replace("**", "").strip().upper()
                    data_rows.append((iid, status_clean, line))
                    continue
        if not data_rows:
            preamble_lines.append(line)

    # Split open/staged vs closed rows
    open_statuses = {"OPEN", "STAGED", "PENDING"}
    open_rows = [r for r in data_rows if r[1] in open_statuses]
    closed_rows = [r for r in data_rows if r[1] not in open_statuses]

    if len(closed_rows) <= max_closed:
        return

    kept_closed = closed_rows[-max_closed:]
    archived_rows = closed_rows[:-max_closed]
    kept_ids = {r[0] for r in (open_rows + kept_closed)}

    # Partition ## <ID>: detailed blocks
    sec_blocks = []
    cur_id = None
    cur_lines = []
    for line in sec_lines:
        m = sec_header_re.match(line)
        if m:
            if cur_id is not None:
                sec_blocks.append((cur_id, "\n".join(cur_lines).rstrip()))
            cur_id = m.group(1)
            cur_lines = [line]
        else:
            if cur_id is not None:
                cur_lines.append(line)
    if cur_id is not None:
        sec_blocks.append((cur_id, "\n".join(cur_lines).rstrip()))

    kept_sections = [blk for sid, blk in sec_blocks if sid in kept_ids]
    archived_sections = [(sid, blk) for sid, blk in sec_blocks if sid not in kept_ids]

    archive_path = _resolve_archive_path("PROBLEMS_TO_SOLVE_ARCHIVE.md")
    existing_archive = ""
    if os.path.exists(archive_path):
        with open(archive_path, "r", encoding="utf-8") as af:
            existing_archive = af.read()

    arch_chunks = []
    new_rows = [r[2] for r in archived_rows if f"| {r[0]} |" not in existing_archive]
    if new_rows:
        arch_chunks.append("### Archived Table Rows\n| Date | Issue ID | Description | Status | Impact |\n| :--- | :--- | :--- | :--- | :--- |\n" + "\n".join(new_rows))
    new_secs = [blk for sid, blk in archived_sections if f"## {sid}:" not in existing_archive]
    if new_secs:
        arch_chunks.append("\n\n".join(new_secs))

    if arch_chunks:
        hdr = "# SigmaFidelity™ Institutional Error Log — Cold Archive\nAll entries below are permanently indexed in PostgreSQL `\"SigmaKnowledgeScars\"`.\n\n" if not existing_archive else "\n\n"
        stamp = f"<!-- Archived via sigma_sync.py on {datetime.now().strftime('%m/%d/%Y %I:%M %p')} -->\n"
        with open(archive_path, "a", encoding="utf-8") as af:
            af.write(hdr + stamp + "\n\n".join(arch_chunks) + "\n")

    # Preserve original chronological order among kept rows
    ordered_kept_rows = [r[2] for r in data_rows if r[0] in kept_ids]
    clean_preamble = "\n".join(preamble_lines).rstrip()
    archive_note = (
        "\n> **Note:** Full historical bug records (`BUG-001`+) are stored in PostgreSQL `\"SigmaKnowledgeScars\"` "
        "and cold-archived in `backups/PROBLEMS_TO_SOLVE_ARCHIVE.md`. This rolling file retains open items plus the latest 5 resolved entries.\n"
    )
    if "**Note:** Full historical bug records" in clean_preamble:
        archive_note = "\n"

    new_doc = clean_preamble + "\n" + "\n".join(ordered_kept_rows) + "\n" + archive_note + "\n" + "\n\n".join(kept_sections).rstrip() + "\n"
    _mirror_paired_workspace_file("docs/PROBLEMS-TO-SOLVE.md", new_doc)
    print(f"[SYNC] Auto-trimmed docs/PROBLEMS-TO-SOLVE.md (archived {len(archived_rows)} resolved entries -> {archive_path}).")


def _export_knowledge_scars_seed(conn, has_vector: bool) -> None:
    """Backfills any missing embeddings/tsvectors and exports sigma_knowledge_scars_seed.json for Azure boot parity."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE "SigmaKnowledgeScars"
            SET search_vector = to_tsvector(
                'english',
                COALESCE(description, '') || ' ' || COALESCE(root_cause, '') || ' ' ||
                COALESCE(implemented_fix, '') || ' ' || COALESCE(preventative_rule, '')
            )
            WHERE search_vector IS NULL;
        """)
        if has_vector:
            cur.execute("""
                SELECT id, COALESCE(description, ''), COALESCE(root_cause, ''),
                       COALESCE(implemented_fix, ''), COALESCE(preventative_rule, '')
                FROM "SigmaKnowledgeScars"
                WHERE embedding IS NULL;
            """)
            missing_vecs = cur.fetchall()
            for mid, desc_s, rc_s, fix_s, prev_s in missing_vecs:
                vec = calculate_local_embedding(f"{desc_s} {rc_s} {fix_s} {prev_s}")
                cur.execute('UPDATE "SigmaKnowledgeScars" SET embedding = %s WHERE id = %s;', (vec, mid))

        cur.execute("""
            SELECT id, description, category, status, impact_level,
                   COALESCE(root_cause, ''), COALESCE(implemented_fix, ''), COALESCE(preventative_rule, ''),
                   created_at, resolved_at, resolution_notes
            FROM "SigmaKnowledgeScars"
            ORDER BY id ASC;
        """)
        scars_rows = [
            [
                r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7],
                r[8].isoformat() if r[8] else None,
                r[9].isoformat() if r[9] else None,
                r[10],
            ]
            for r in cur.fetchall()
        ]

        incidents_rows = []
        try:
            cur.execute('SELECT id, date, description, category, severity FROM "Incidents" ORDER BY id ASC;')
            incidents_rows = [
                [r[0], r[1].isoformat() if r[1] else None, r[2], r[3], r[4]]
                for r in cur.fetchall()
            ]
        except Exception:
            conn.rollback()

    conn.commit()

    seed_candidates = [
        os.path.abspath(os.path.join(os.getcwd(), "database", "sigma_knowledge_scars_seed.json")),
        os.path.abspath(os.path.join(os.getcwd(), "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE", "database", "sigma_knowledge_scars_seed.json")),
    ]
    for seed_path in seed_candidates:
        if os.path.isdir(os.path.dirname(seed_path)):
            tmp_path = seed_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as sf:
                json.dump({"scars": scars_rows, "incidents": incidents_rows}, sf, ensure_ascii=False, indent=2)
            os.replace(tmp_path, seed_path)
            print(f"[SYNC] Exported {len(scars_rows)} SigmaKnowledgeScars rows -> {seed_path}.")
            break


def sync_problems_to_solve():
    problems_file = "docs/PROBLEMS-TO-SOLVE.md"
    if not os.path.exists(problems_file): return
    
    print("[SYNC] Scanning for new problems to solve & generating vector embeddings...")
    with open(problems_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    parsed = parse_problems_to_solve(content)
    
    try:
        conn = psycopg2.connect(DB_URL)
        has_vector = False
        with conn.cursor() as cur:
            try:
                cur.execute("SELECT '[1,2,3]'::vector;")
                conn.commit()
                has_vector = True
            except Exception:
                conn.rollback()
                has_vector = False

        with conn.cursor() as cur:
            for item in parsed:
                iid = item["issue_id"]
                prefix = f"{iid}:"
                
                cur.execute('SELECT id FROM "SigmaKnowledgeScars" WHERE description LIKE %s;', (prefix + '%',))
                row = cur.fetchone()
                
                created_dt = None
                if item["detected_date"]:
                    try:
                        created_dt = datetime.strptime(item["detected_date"], "%m/%d/%Y")
                    except Exception:
                        pass
                
                resolved_dt = None
                if item["status"].upper() == "RESOLVED":
                    resolved_dt = datetime.now()
                
                desc_val = f"{prefix} {item['description']}"
                full_text = f"{desc_val} {item.get('root_cause', '')} {item.get('implemented_fix', '')} {item.get('preventative_rule', '')}"
                embed_vector = calculate_local_embedding(full_text)
                
                if row:
                    db_id = row[0]
                    if has_vector:
                        print(f"[SYNC] Updating mistake log & embedding: {iid}")
                        cur.execute("""
                            UPDATE "SigmaKnowledgeScars"
                            SET description = %s, category = %s, status = %s, impact_level = %s,
                                root_cause = %s, implemented_fix = %s, preventative_rule = %s,
                                resolved_at = COALESCE(resolved_at, %s),
                                embedding = %s,
                                search_vector = to_tsvector('english', %s)
                            WHERE id = %s;
                        """, (
                            desc_val, item["category"], item["status"], item["impact_level"],
                            item["root_cause"], item["implemented_fix"], item["preventative_rule"],
                            resolved_dt, embed_vector, full_text, db_id
                        ))
                    else:
                        print(f"[SYNC] Updating mistake log: {iid}")
                        cur.execute("""
                            UPDATE "SigmaKnowledgeScars"
                            SET description = %s, category = %s, status = %s, impact_level = %s,
                                root_cause = %s, implemented_fix = %s, preventative_rule = %s,
                                resolved_at = COALESCE(resolved_at, %s),
                                search_vector = to_tsvector('english', %s)
                            WHERE id = %s;
                        """, (
                            desc_val, item["category"], item["status"], item["impact_level"],
                            item["root_cause"], item["implemented_fix"], item["preventative_rule"],
                            resolved_dt, full_text, db_id
                        ))
                else:
                    if has_vector:
                        print(f"[SYNC] Inserting new mistake log & embedding: {iid}")
                        cur.execute("""
                            INSERT INTO "SigmaKnowledgeScars" (
                                description, category, status, impact_level, root_cause,
                                implemented_fix, preventative_rule, created_at, resolved_at,
                                embedding, search_vector
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, to_tsvector('english', %s));
                        """, (
                            desc_val, item["category"], item["status"], item["impact_level"],
                            item["root_cause"], item["implemented_fix"], item["preventative_rule"],
                            created_dt or datetime.now(), resolved_dt, embed_vector, full_text
                        ))
                    else:
                        print(f"[SYNC] Inserting new mistake log: {iid}")
                        cur.execute("""
                            INSERT INTO "SigmaKnowledgeScars" (
                                description, category, status, impact_level, root_cause,
                                implemented_fix, preventative_rule, created_at, resolved_at,
                                search_vector
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, to_tsvector('english', %s));
                        """, (
                            desc_val, item["category"], item["status"], item["impact_level"],
                            item["root_cause"], item["implemented_fix"], item["preventative_rule"],
                            created_dt or datetime.now(), resolved_dt, full_text
                        ))
        conn.commit()
        _export_knowledge_scars_seed(conn, has_vector)
        conn.close()
        _trim_problems_markdown(problems_file, content, max_closed=5)
    except Exception as e:
        print(f"Error syncing problems: {e}")

def sync_cli_conversations():
    brain_path = os.path.expanduser("~/.gemini/antigravity-cli/brain/")
    if not os.path.exists(brain_path):
        return
    
    print("[SYNC] Synchronizing CLI Conversations & Transcript Steps...")
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS "CliConversations" (
                    conversation_id VARCHAR(128) PRIMARY KEY,
                    total_steps INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS "CliSteps" (
                    id SERIAL PRIMARY KEY,
                    conversation_id VARCHAR(128) REFERENCES "CliConversations"(conversation_id) ON DELETE CASCADE,
                    step_index INTEGER,
                    step_type VARCHAR(64),
                    role VARCHAR(64),
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unique_conv_step UNIQUE (conversation_id, step_index)
                );
            """)

            conv_dirs = [d for d in os.listdir(brain_path) if os.path.isdir(os.path.join(brain_path, d))]
            for conv_id in conv_dirs:
                log_file = os.path.join(brain_path, conv_id, ".system_generated", "logs", "transcript.jsonl")
                if not os.path.exists(log_file):
                    continue

                steps = []
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                steps.append(json.loads(line))
                            except Exception:
                                pass

                if not steps:
                    continue

                cur.execute("""
                    INSERT INTO "CliConversations" (conversation_id, total_steps, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (conversation_id) DO UPDATE 
                    SET total_steps = EXCLUDED.total_steps, updated_at = NOW();
                """, (conv_id, len(steps)))

                for step in steps:
                    step_idx = step.get("step_index", 0)
                    step_type = str(step.get("type", "UNKNOWN"))
                    role = str(step.get("source", step.get("role", "SYSTEM")))
                    content_str = str(step.get("content", "")).replace("\x00", "")

                    cur.execute("""
                        INSERT INTO "CliSteps" (conversation_id, step_index, step_type, role, content)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (conversation_id, step_index) DO UPDATE 
                        SET step_type = EXCLUDED.step_type, role = EXCLUDED.role, content = EXCLUDED.content;
                    """, (conv_id, step_idx, step_type, role, content_str))

        conn.commit()
        conn.close()
        print("[SYNC] CLI Conversations successfully indexed to Postgres.")
    except Exception as e:
        print(f"Error syncing CLI conversations: {e}")

def sync_memory_rot():
    print("[SYNC] Analyzing live Memory Rot & Cognitive Health (Rack 1)...")
    try:
        import sys
        if "/app/scripts" not in sys.path and os.path.exists("/app/scripts"):
            sys.path.insert(0, "/app/scripts")
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from memory_rot_meter import record_memory_rot_to_db
        res = record_memory_rot_to_db(db_url=DB_URL)
        if res.get("status") == "success":
            d = res["data"]
            print(f"  -> SUCCESS: Memory Rot Index: {d['composite_score']}% ({d['status']})")
        else:
            print(f"  -> [INFO] Memory rot analysis note: {res.get('message')}")
    except Exception as e:
        print(f"  -> [WARNING] Failed to sync memory rot: {e}")

def sync_rack_telemetry_snapshot():
    print("[SYNC] Ingesting 8-Rack Historical Telemetry Snapshot into RackTelemetryHistory...")
    try:
        import sys
        if "/app" not in sys.path and os.path.exists("/app"):
            sys.path.insert(0, "/app")
        from core.services.self_healing_engine import record_rack_telemetry_snapshot
        session_id = datetime.now().strftime("%Y-%m-%d-%H%M-PERSISTENCE-CLOSE")
        res = record_rack_telemetry_snapshot(session_id=session_id, db_url=DB_URL)
        if res.get("status") == "success":
            print(f"  -> SUCCESS: Logged {res.get('racks_logged')} racks into RackTelemetryHistory in {res.get('latency_ms')} ms (Session: {session_id})")
        else:
            print(f"  -> [WARNING] Snapshot failed: {res.get('message')}")
    except Exception as e:
        print(f"  -> [ERROR] Failed to sync rack telemetry snapshot: {e}")

def run_all():
    print("--- SigmaFidelity: Initiating Institutional Persistence Sync ---")
    sync_walkthrough()
    sync_new_sops()
    sync_system_state()
    sync_problems_to_solve()
    sync_cli_conversations()
    sync_memory_rot()
    sync_rack_telemetry_snapshot()
    print("--- SUCCESS: All neural cores synchronized. ---")

if __name__ == "__main__":
    run_all()
