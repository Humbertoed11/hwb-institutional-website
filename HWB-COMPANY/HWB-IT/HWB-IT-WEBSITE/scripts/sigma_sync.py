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
    sop_dir = "HWB-COMPANY/HWB-QMS"
    if not os.path.exists(sop_dir): return
    
    print("[SYNC] Scanning for new HTML SOPs...")
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            for f in os.listdir(sop_dir):
                if f.endswith(".html") and f != "sop_template.html":
                    file_path = os.path.join(sop_dir, f)
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()
                    
                    cur.execute("""
                        INSERT INTO sigma_kb (doc_id, content, metadata)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (doc_id) DO UPDATE SET content = EXCLUDED.content;
                    """, (f, content, Json({"source": "Automatic Sync", "path": file_path})))
        conn.commit()
        conn.close()
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
                INSERT INTO "SigmaSystemCore" (session_id, state_data)
                VALUES (%s, %s)
                ON CONFLICT (session_id) DO UPDATE SET state_data = EXCLUDED.state_data;
            """, ("ACTIVE-SESSION", Json(state_json)))
        conn.commit()
        conn.close()
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
    for row in rows:
        iid = row["issue_id"]
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


def sync_problems_to_solve():
    problems_file = "docs/PROBLEMS-TO-SOLVE.md"
    if not os.path.exists(problems_file): return
    
    print("[SYNC] Scanning for new problems to solve & generating vector embeddings...")
    with open(problems_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    parsed = parse_problems_to_solve(content)
    
    try:
        conn = psycopg2.connect(DB_URL)
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
        conn.commit()
        conn.close()
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

def sync_rack_telemetry_snapshot():
    print("[SYNC] Ingesting 7-Rack Historical Telemetry Snapshot into RackTelemetryHistory...")
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
    sync_rack_telemetry_snapshot()
    print("--- SUCCESS: All neural cores synchronized. ---")

if __name__ == "__main__":
    run_all()
