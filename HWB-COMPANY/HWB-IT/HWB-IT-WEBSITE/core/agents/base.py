import os
import datetime
import traceback
import json
from google import genai
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ValidationError
from core.services.database import get_db, db_cursor
from core.models.memory_tier4 import Tier4Model, LeadModel, CustomerModel, OpportunityModel, MilestoneModel

# --- SigmaFidelity™ Enterprise Agent Base ---
# Version: 2.4.0 (Pipeline Logic Integrated)
# Mandate: HWB-QMS-9.8 (Relational Memory)
# Updated: Added Opportunity Pipeline Stage-Gates and Stagnation Logic

class SigmaAgent(ABC):
    def __init__(self, agent_id: str, db_url: Optional[str] = None):
        self.agent_id = agent_id
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.error_threshold = 3
        self.error_count = 0
        
        # Configure Modern Gemini Client
        api_key = os.getenv("GOOGLE_API_KEY")
        self.client = None
        if api_key:
            self.client = genai.Client(api_key=api_key)
            
        self.setup_telemetry_tables()

    def setup_telemetry_tables(self):
        """Ensures the institutional telemetry and state tables exist."""
        sql_sqlite = [
            "CREATE TABLE IF NOT EXISTS agent_telemetry (id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT, task_id TEXT, action TEXT, status TEXT, data TEXT, error TEXT, timestamp DATETIME)",
            "CREATE TABLE IF NOT EXISTS agent_task_state (task_id TEXT PRIMARY KEY, agent_id TEXT, current_step INTEGER, total_steps INTEGER, status TEXT, last_updated DATETIME)",
            "CREATE TABLE IF NOT EXISTS institutional_friction (id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT, issue TEXT, stack_trace TEXT, status TEXT, timestamp DATETIME)",
            "CREATE TABLE IF NOT EXISTS sigma_kb (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id TEXT UNIQUE, content TEXT, metadata TEXT, timestamp DATETIME)"
        ]
        sql_pg = [
            "CREATE TABLE IF NOT EXISTS agent_telemetry (id SERIAL PRIMARY KEY, agent_id TEXT, task_id TEXT, action TEXT, status TEXT, data TEXT, error TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS agent_task_state (task_id TEXT PRIMARY KEY, agent_id TEXT, current_step INTEGER, total_steps INTEGER, status TEXT, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS institutional_friction (id SERIAL PRIMARY KEY, agent_id TEXT, issue TEXT, stack_trace TEXT, status TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS sigma_kb (id SERIAL PRIMARY KEY, doc_id TEXT UNIQUE, content TEXT, search_vector tsvector, embedding vector(768), metadata JSONB, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE INDEX IF NOT EXISTS sigma_kb_search_idx ON sigma_kb USING GIN(search_vector)",
            "CREATE INDEX IF NOT EXISTS sigma_kb_vector_idx ON sigma_kb USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
        ]
        
        scheme = "postgres" if "postgres" in self.db_url else "sqlite"
        statements = sql_pg if scheme == "postgres" else sql_sqlite
        
        try:
            with db_cursor(self.db_url) as cur:
                for stmt in statements:
                    try:
                        cur.execute(stmt)
                    except Exception as inner_e:
                        if "vector" in str(inner_e).lower(): continue
                        raise inner_e
        except Exception as e:
            print(f"[FATAL] Failed to initialize telemetry for {self.agent_id}: {e}", flush=True)

    def upsert_tier4_record(self, table_name: str, model: Tier4Model, conflict_col: str = "id"):
        """Tier 4 Structured Operational Memory: Validated Transactional Upsert."""
        try:
            data = model.model_dump(exclude_unset=True)
            cols = list(data.keys())
            vals = list(data.values())
            
            # Quote table name for case-sensitivity (Postgres)
            quoted_table = f'"{table_name}"'
            
            with db_cursor(self.db_url) as cur:
                if "postgres" in self.db_url:
                    placeholders = ", ".join(["%s"] * len(cols))
                    update_stmt = ", ".join([f"{c} = EXCLUDED.{c}" for c in cols if c != conflict_col])
                    sql = f"""
                        INSERT INTO {quoted_table} ({", ".join(cols)})
                        VALUES ({placeholders})
                        ON CONFLICT ({conflict_col}) DO UPDATE SET
                        {update_stmt}
                    """
                    cur.execute(sql, vals)
                else:
                    placeholders = ", ".join(["?"] * len(cols))
                    sql = f"INSERT OR REPLACE INTO {quoted_table} ({", ".join(cols)}) VALUES ({placeholders})"
                    cur.execute(sql, vals)
            
            print(f"[{self.agent_id}] Tier 4 Record Upserted into {table_name}", flush=True)
            return True
        except Exception as e:
            print(f"[ERROR] Tier 4 Upsert failed for {table_name}: {e}", flush=True)
            return False

    def fetch_tier4_records(self, table_name: str, filters: Optional[Dict[str, Any]] = None, limit: int = 100):
        """Tier 4 Structured Operational Memory: Validated Retrieval."""
        try:
            quoted_table = f'"{table_name}"'
            sql = f"SELECT * FROM {quoted_table}"
            vals = []
            
            if filters:
                where_clause = " WHERE " + " AND ".join([f"{k} = %s" if "postgres" in self.db_url else f"{k} = ?" for k in filters.keys()])
                sql += where_clause
                vals = list(filters.values())
            
            sql += f" LIMIT {limit}"
            
            results = []
            with db_cursor(self.db_url) as cur:
                cur.execute(sql, vals)
                rows = cur.fetchall()
                for row in rows:
                    results.append(dict(row))
            return results
        except Exception as e:
            print(f"[ERROR] Tier 4 Retrieval failed for {table_name}: {e}", flush=True)
            return []

    def convert_lead_to_customer(self, lead_id: int, company_details: Optional[Dict] = None):
        """
        Tier 4 Atomic Transaction: Logic Gate for Lead-to-Customer conversion.
        Ensures 100% data continuity across Leads, Customers, and GlobalActivities.
        """
        try:
            with db_cursor(self.db_url) as cur:
                # 1. Fetch Lead
                cur.execute('SELECT * FROM "Leads" WHERE id = %s', (lead_id,))
                lead_data = cur.fetchone()
                if not lead_data:
                    raise Exception(f"Lead ID {lead_id} not found.")
                
                lead = dict(lead_data)
                
                # 2. Create Customer Model
                customer = CustomerModel(
                    company_name=lead['center_name'] or "Unknown Entity",
                    company_address=lead['address'] or "N/A",
                    city=lead['city'],
                    state=lead['state'],
                    zip=lead['zipcode'],
                    email=lead['email'],
                    phone=lead['phone'],
                    sqf=lead['sqf'] or 0,
                    status="Active",
                    notes=f"Converted from Lead {lead_id}. {company_details.get('notes', '') if company_details else ''}"
                )
                
                cust_data = customer.model_dump(exclude_unset=True)
                cols = list(cust_data.keys())
                vals = list(cust_data.values())
                
                # 3. Atomic Insert into Customers
                placeholders = ", ".join(["%s"] * len(cols))
                cur.execute(f'INSERT INTO "Customers" ({", ".join(cols)}) VALUES ({placeholders}) RETURNING customer_id', vals)
                customer_id = cur.fetchone()[0]
                
                # 4. Atomic Update Lead Status
                cur.execute('UPDATE "Leads" SET status = %s, is_converted = %s, updated_at = %s WHERE id = %s', 
                             ("Converted", True, datetime.datetime.now().date(), lead_id))
                
                # 5. Log Episodic Event (Internal RAG/Audit)
                description = f"[{self.agent_id}] Converted Lead {lead_id} to Customer {customer_id} ({customer.company_name})"
                cur.execute("""
                    INSERT INTO "GlobalActivities" (parent_type, activity_type, description, timestamp)
                    VALUES (%s, %s, %s, %s)
                """, ("Account", "Conversion", description, datetime.datetime.now()))
                
            print(f"[{self.agent_id}] Lead {lead_id} successfully converted to Customer {customer_id}.", flush=True)
            return customer_id
        except Exception as e:
            print(f"[ERROR] Lead conversion transaction failed: {e}", flush=True)
            return None

    def update_opportunity_stage(self, opp_id: int, new_stage: str):
        """
        Tier 4 Opportunity Pipeline Logic: Deterministic Stage-Gate Progression.
        Automatically updates probability and logs the transition.
        """
        stages = {
            "Discovery": 10,
            "Qualification": 30,
            "Proposal": 60,
            "Negotiation": 80,
            "Closed-Won": 100,
            "Closed-Lost": 0
        }
        
        if new_stage not in stages:
            print(f"[ERROR] Invalid stage: {new_stage}. Must be one of {list(stages.keys())}", flush=True)
            return False
            
        try:
            probability = stages[new_stage]
            with db_cursor(self.db_url) as cur:
                cur.execute("""
                    UPDATE "Opportunities" 
                    SET stage = %s, probability = %s, last_modified = CURRENT_DATE 
                    WHERE opp_id = %s
                """, (new_stage, probability, opp_id))
                
                # Log transition as Episodic Memory
                self.log_episodic_event(
                    task_id=f"OPP_UPDATE_{opp_id}",
                    event_name="PIPELINE_TRANSITION",
                    rationale=f"Opportunity {opp_id} moved to {new_stage} stage based on agent evaluation.",
                    result=f"Probability updated to {probability}%."
                )
            return True
        except Exception as e:
            print(f"[ERROR] Opportunity stage update failed: {e}", flush=True)
            return False

    def check_opportunity_stagnation(self, threshold_days: int = 15):
        """
        Stagnation Circuit Breaker: Logs institutional friction for idle deals.
        Mandate: SigmaFidelity™ Velocity Protocol.
        """
        try:
            stagnant_opps = []
            with db_cursor(self.db_url) as cur:
                cur.execute("""
                    SELECT opp_id, stage, last_modified 
                    FROM "Opportunities" 
                    WHERE stage NOT IN ('Closed-Won', 'Closed-Lost')
                    AND last_modified < CURRENT_DATE - INTERVAL '%s days'
                """, (threshold_days,))
                rows = cur.fetchall()
                for row in rows:
                    stagnant_opps.append(dict(row))
                    
                    # Log Friction Event
                    self.log_friction(
                        issue=f"Opportunity {row['opp_id']} STAGNANT in {row['stage']} stage.",
                        stack_trace=f"Threshold exceeded: {threshold_days} days since last modification ({row['last_modified']})."
                    )
            return stagnant_opps
        except Exception as e:
            print(f"[ERROR] Stagnation check failed: {e}", flush=True)
            return []

    def generate_embedding(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> Optional[List[float]]:
        """Generates a 768-dimensional embedding vector via the modern google-genai SDK."""
        try:
            if not self.client:
                print("[ERROR] GenAI Client not initialized.", flush=True)
                return None
                
            result = self.client.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
                config={
                    "task_type": task_type,
                    "output_dimensionality": 768
                }
            )
            return result.embeddings[0].values
        except Exception as e:
            print(f"[ERROR] Embedding generation failed: {e}", flush=True)
            return None

    def chunk_content(self, content: str, max_chars: int = 2000, overlap: int = 200) -> List[str]:
        """Recursive Character Splitting logic to prevent oversized chunks."""
        chunks = []
        if len(content) <= max_chars:
            return [content]
            
        # Recursive split: Paragraph -> Sentence -> Space
        separators = ["\n\n", "\n", ". ", " "]
        
        def recursive_split(text: str, seps: List[str]) -> List[str]:
            if len(text) <= max_chars:
                return [text]
            if not seps:
                return [text[i:i+max_chars] for i in range(0, len(text), max_chars - overlap)]
            
            sep = seps[0]
            parts = text.split(sep)
            final_parts = []
            current_chunk = ""
            
            for part in parts:
                if len(current_chunk) + len(part) + len(sep) <= max_chars:
                    current_chunk += (sep if current_chunk else "") + part
                else:
                    if current_chunk:
                        final_parts.append(current_chunk)
                    # If a single part is still too long, recurse with next separator
                    if len(part) > max_chars:
                        final_parts.extend(recursive_split(part, seps[1:]))
                        current_chunk = ""
                    else:
                        current_chunk = part
            
            if current_chunk:
                final_parts.append(current_chunk)
            return final_parts

        return recursive_split(content, separators)

    def ingest_into_kb(self, doc_id: str, content: str, metadata: Optional[Dict] = None):
        """Tier 3 Semantic Memory: Hardened Ingestion with Recursive Chunking and Metadata Enforcement."""
        try:
            if not content.strip():
                print(f"[WARN] Skipping ingestion for {doc_id}: Content is empty.", flush=True)
                return False
            
            # 1. Enforce Metadata Schema (HWB-QMS-9.8)
            enriched_metadata = metadata or {}
            enriched_metadata.setdefault("department", "GENERAL")
            enriched_metadata.setdefault("security_clearance", 1) # Default: Level 1 (Public)
            enriched_metadata.setdefault("author_id", self.agent_id)
            enriched_metadata["ingested_at"] = datetime.datetime.now().isoformat()
            
            # 2. Recursive Chunking
            chunks = self.chunk_content(content)
            
            with db_cursor(self.db_url) as cur:
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{doc_id}_chunk_{i}"
                    embedding = self.generate_embedding(chunk, task_type="RETRIEVAL_DOCUMENT")
                    meta_json = json.dumps(enriched_metadata)
                    
                    if "postgres" in self.db_url:
                        cur.execute("""
                            INSERT INTO sigma_kb (doc_id, content, search_vector, embedding, metadata)
                            VALUES (%s, %s, to_tsvector(%s), %s, %s)
                            ON CONFLICT (doc_id) DO UPDATE SET
                            content = EXCLUDED.content,
                            search_vector = EXCLUDED.search_vector,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata
                        """, (chunk_id, chunk, chunk, embedding, meta_json))
                    else:
                        cur.execute("INSERT OR REPLACE INTO sigma_kb (doc_id, content, metadata) VALUES (?, ?, ?)", 
                                     (chunk_id, chunk, meta_json))
            
            print(f"[{self.agent_id}] Knowledge Ingested: {doc_id} ({len(chunks)} chunks)", flush=True)
            return True
        except Exception as e:
            print(f"[ERROR] KB Ingestion failed for {doc_id}: {e}", flush=True)
            return False

    def retrieve_semantic_context(self, query: str, limit: int = 5, min_clearance: int = 1):
        """Tier 3 Semantic Memory: Hybrid Search (Vector + FTS) with RRF Ranking and Access Control."""
        try:
            results = []
            embedding = self.generate_embedding(query, task_type="RETRIEVAL_QUERY")
            
            with db_cursor(self.db_url) as cur:
                if "postgres" in self.db_url:
                    # 1. Reciprocal Rank Fusion (RRF) Logic: Combine Semantic and Keyword Search
                    # Filtered by Security Clearance (Access Control)
                    sql = """
                        WITH vector_search AS (
                            SELECT doc_id, content, 1 - (embedding <=> %s::vector) as similarity,
                                   ROW_NUMBER() OVER (ORDER BY (embedding <=> %s::vector)) as rank
                            FROM sigma_kb
                            WHERE embedding IS NOT NULL 
                            AND (metadata->>'security_clearance')::int <= %s
                        ),
                        keyword_search AS (
                            SELECT doc_id, content, ts_rank(search_vector, plainto_tsquery(%s)) as similarity,
                                   ROW_NUMBER() OVER (ORDER BY ts_rank(search_vector, plainto_tsquery(%s)) DESC) as rank
                            FROM sigma_kb
                            WHERE search_vector @@ plainto_tsquery(%s)
                            AND (metadata->>'security_clearance')::int <= %s
                        )
                        SELECT COALESCE(v.doc_id, k.doc_id) as doc_id, 
                               COALESCE(v.content, k.content) as content,
                               (COALESCE(1.0 / (60 + v.rank), 0.0) + COALESCE(1.0 / (60 + k.rank), 0.0)) as rrf_score
                        FROM vector_search v
                        FULL OUTER JOIN keyword_search k ON v.doc_id = k.doc_id
                        ORDER BY rrf_score DESC
                        LIMIT %s
                    """
                    cur.execute(sql, (embedding, embedding, min_clearance, query, query, query, min_clearance, limit))
                else:
                    # SQLite Fallback
                    cur.execute("""
                        SELECT doc_id, content, 1.0 as similarity
                        FROM sigma_kb
                        WHERE content LIKE ?
                        LIMIT ?
                    """, (f"%{query}%", limit))
                
                rows = cur.fetchall()
                for row in rows:
                    results.append({"doc_id": row[0], "content": row[1], "score": float(row[2])})
            
            return results
        except Exception as e:
            print(f"[ERROR] Semantic retrieval failed for {self.agent_id}: {e}", flush=True)
            return []

    def log_telemetry(self, task_id: str, action: str, status: str, data: Optional[Dict] = None, error: Optional[str] = None):
        """Standardized SQL Telemetry Logging."""
        try:
            with db_cursor(self.db_url) as cur:
                data_json = json.dumps(data) if data else None
                if "postgres" in self.db_url:
                    cur.execute("""INSERT INTO agent_telemetry (agent_id, task_id, action, status, data, error) 
                                 VALUES (%s, %s, %s, %s, %s, %s)""", 
                                 (self.agent_id, task_id, action, status, data_json, error))
                else:
                    cur.execute("""INSERT INTO agent_telemetry (agent_id, task_id, action, status, data, error, timestamp) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?)""", 
                                 (self.agent_id, task_id, action, status, data_json, error, datetime.datetime.now()))
        except Exception as e:
            print(f"[ERROR] Telemetry logging failed for {self.agent_id}: {e}", flush=True)

    def log_episodic_event(self, task_id: str, event_name: str, rationale: str, result: str, metadata: Optional[Dict] = None):
        """Tier 5 Episodic Memory: Captures the 'Why' and 'How' for institutional auditing."""
        try:
            timestamp = datetime.datetime.now()
            full_data = {
                "rationale": rationale,
                "result": result,
                "metadata": metadata or {}
            }
            
            # 1. Technical Telemetry (Tier 5 - Audit Layer)
            self.log_telemetry(task_id, event_name, "COMPLETED", data=full_data)
            
            # 2. Institutional Audit (GlobalActivities)
            with db_cursor(self.db_url) as cur:
                if "postgres" in self.db_url:
                    # GlobalActivities: activity_id, parent_id, parent_type, activity_type, description, timestamp
                    description = f"[{self.agent_id}] {rationale[:100]}... Result: {result}"
                    cur.execute("""
                        INSERT INTO "GlobalActivities" (parent_type, activity_type, description, timestamp)
                        VALUES (%s, %s, %s, %s)
                    """, ("Agent", event_name, description, timestamp))
                    
                    # 3. Autonomous Labor Log (ActivityLog)
                    cur.execute("""
                        INSERT INTO "ActivityLog" (date, activity_name, hours, category)
                        VALUES (%s, %s, %s, %s)
                    """, (timestamp.date(), f"Autonomous: {event_name} ({self.agent_id})", 0.1, "Autonomous"))
            
            print(f"[{self.agent_id}] Episodic Event Logged: {event_name}", flush=True)
            return True
        except Exception as e:
            print(f"[ERROR] Episodic logging failed for {self.agent_id}: {e}", flush=True)
            return False

    def update_task_state(self, task_id: str, current_step: int, total_steps: int, status: str):
        """Tier 2 Working Memory: Persists the active state of an ongoing task."""
        try:
            with db_cursor(self.db_url) as cur:
                if "postgres" in self.db_url:
                    cur.execute("""INSERT INTO agent_task_state (task_id, agent_id, current_step, total_steps, status, last_updated)
                                 VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                                 ON CONFLICT (task_id) DO UPDATE SET 
                                 current_step = EXCLUDED.current_step,
                                 total_steps = EXCLUDED.total_steps,
                                 status = EXCLUDED.status,
                                 last_updated = CURRENT_TIMESTAMP""",
                                 (task_id, self.agent_id, current_step, total_steps, status))
                else:
                    cur.execute("""INSERT OR REPLACE INTO agent_task_state (task_id, agent_id, current_step, total_steps, status, last_updated)
                                 VALUES (?, ?, ?, ?, ?, ?)""",
                                 (task_id, self.agent_id, current_step, total_steps, status, datetime.datetime.now()))
            print(f"[{self.agent_id}] Task {task_id} State Updated: Step {current_step}/{total_steps} ({status})", flush=True)
        except Exception as e:
            print(f"[ERROR] Task state update failed for {self.agent_id}: {e}", flush=True)

    def log_friction(self, issue: str, stack_trace: str):
        """Automatic Friction Logging to PostgreSQL and Markdown."""
        try:
            # 1. SQL Log
            with db_cursor(self.db_url) as cur:
                if "postgres" in self.db_url:
                    cur.execute("INSERT INTO institutional_friction (agent_id, issue, stack_trace, status) VALUES (%s, %s, %s, %s)",
                                 (self.agent_id, issue, stack_trace, "OPEN"))
                else:
                    cur.execute("INSERT INTO institutional_friction (agent_id, issue, stack_trace, status, timestamp) VALUES (?, ?, ?, ?, ?)",
                                 (self.agent_id, issue, stack_trace, "OPEN", datetime.datetime.now()))
            
            # 2. Markdown Audit Trail (HWB-QMS-10.2)
            friction_file = "docs/PROBLEMS-TO-SOLVE.md"
            log_entry = f"| {datetime.datetime.now().strftime('%Y-%m-%d')} | **{self.agent_id} Failure** - {issue[:50]}... | High | OPEN | George |\n"
            
            if os.path.exists(friction_file):
                with open(friction_file, 'a') as f:
                    f.write(log_entry)
        except Exception as e:
            print(f"[ERROR] Friction logging failed for {self.agent_id}: {e}", flush=True)

    def handle_error(self, task_id: str, error: Exception):
        """Industrial Circuit Breaker Logic."""
        self.error_count += 1
        stack = traceback.format_exc()
        self.log_telemetry(task_id, "ERROR_HANDLING", "FAILED", error=str(error))
        
        if self.error_count >= self.error_threshold:
            self.log_friction(f"Circuit Breaker Tripped: {str(error)}", stack)
            print(f"[CRITICAL] Agent {self.agent_id} TRIPPED CIRCUIT BREAKER. Execution Halted.", flush=True)
            return True # Signal Hard Break
        
        print(f"[WARN] Agent {self.agent_id} encountered error ({self.error_count}/{self.error_threshold}): {error}", flush=True)
        return False # Signal Retry

    @abstractmethod
    def execute(self, task_data: Any):
        """The core execution logic for the agent."""
        pass
