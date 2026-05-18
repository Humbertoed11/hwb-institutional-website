import os
import sys
import json
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

# Ensure core is importable
sys.path.append('HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE')
from core.agents.orchestrator import SigmaOrchestrator

def ingest_all():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    
    print("--- SigmaFidelity: Initiating Mass Semantic Ingestion ---")
    orch = SigmaOrchestrator(db_url=db_url)
    
    # 1. Ingest Markdown SOPs
    print("[1/2] Ingesting Institutional SOPs...")
    sop_count = 0
    for root, dirs, files in os.walk("HWB-COMPANY"):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if content.strip():
                            doc_id = file_path.replace("HWB-COMPANY/", "").replace("/", "_")
                            metadata = {
                                "path": file_path,
                                "type": "SOP",
                                "extension": "md",
                                "ingested_at": datetime.now().isoformat()
                            }
                            orch.ingest_into_kb(doc_id, content, metadata)
                            sop_count += 1
                except Exception as e:
                    print(f"[WARN] Failed to ingest {file_path}: {e}")

    # 2. Ingest Session Logs (Recent Memory)
    print(f"[2/2] Ingesting Session History (logs.json)...")
    try:
        with open("logs.json", "r") as f:
            logs = json.load(f)
            # Ingest in chunks of 20 messages to maintain context
            for i in range(0, len(logs), 20):
                chunk = logs[i:i+20]
                content = json.dumps(chunk, indent=2)
                doc_id = f"SESSION_HISTORY_CHUNK_{i}"
                metadata = {"type": "history", "chunk_index": i}
                orch.ingest_into_kb(doc_id, content, metadata)
    except Exception as e:
        print(f"[WARN] Failed to ingest session history: {e}")

    print(f"--- Ingestion Complete. Ingested {sop_count} SOPs. ---")

if __name__ == "__main__":
    ingest_all()
