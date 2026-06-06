import sys
import os
import json
import psycopg2

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def sync_transcript(file_path):
    if not os.path.exists(file_path):
        print(f"FAILURE: File not found at {file_path}")
        return

    print(f"--- George Bytes: Synchronizing Transcripts from {file_path} ---")
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    step = json.loads(line)
                except Exception:
                    continue
                
                step_index = step.get("step_index")
                source = step.get("source")
                step_type = step.get("type")
                content = step.get("content", "")
                
                if step_type == "USER_INPUT":
                    # Avoid duplicates by matching step_index
                    cur.execute("""
                        SELECT id FROM "HEX_InteractionCore"
                        WHERE technical_data->>'step_index' = %s AND user_prompt = %s
                    """, (str(step_index), content))
                    if not cur.fetchone():
                        cur.execute("""
                            INSERT INTO "HEX_InteractionCore" (user_prompt, status, technical_data)
                            VALUES (%s, %s, %s)
                        """, (content, "SUCCESS", json.dumps({"step_index": step_index, "source": source})))
                elif step_type == "PLANNER_RESPONSE":
                    # Update preceding prompt with planner response
                    cur.execute("""
                        SELECT id FROM "HEX_InteractionCore"
                        ORDER BY id DESC LIMIT 1
                    """)
                    row = cur.fetchone()
                    if row:
                        cur.execute("""
                            UPDATE "HEX_InteractionCore"
                            SET agent_explanation = %s, tools_used = %s
                            WHERE id = %s
                        """, (content, json.dumps(step.get("tool_calls", [])), row[0]))

        conn.commit()
        conn.close()
        print("SUCCESS: Transcript synchronization completed.")
    except Exception as e:
        print(f"ERROR: Sync failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python HEX-SYNC-TRANSCRIPT.py <path_to_transcript.jsonl>")
    else:
        sync_transcript(sys.argv[1])
