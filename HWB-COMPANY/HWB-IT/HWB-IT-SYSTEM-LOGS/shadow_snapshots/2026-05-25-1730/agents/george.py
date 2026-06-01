import os
import sqlite3
import datetime
import requests
import json
from typing import Any, Optional
from pydantic import BaseModel, Field
from core.agents.base import SigmaAgent

# --- SigmaFidelity™ George Agent (Federal Bridge) ---
# Version: 1.4.1 (Enterprise Hardened)
# Mandate: HWB-QMS-9.2 (Robustness, Telemetry)
# Updated: Added flush=True for containerized logging

class SAMOpportunity(BaseModel):
    notice_id: str = Field(alias="noticeId")
    title: str
    naics: str = "561720"
    state: Optional[str] = None
    url: str = Field(alias="uiLink")
    posted_date: str = Field(alias="postedDate")

class GeorgeAgent(SigmaAgent):
    def __init__(self, db_url: Optional[str] = None):
        super().__init__(agent_id="George", db_url=db_url)
        self.api_endpoint = "https://api.sam.gov/opportunities/v2/search"
        self.naics_codes = ["561720", "561210"]

    def execute(self, task_data: Any):
        task_id = task_data.get("task_id", "MANUAL")
        payload = task_data.get("payload", {})
        state = payload.get("state")
        days = payload.get("days", 30)

        return self.sync_sam(task_id, state, days)

    def get_api_key(self):
        return os.getenv("SAM_API_KEY")

    def sync_sam(self, task_id: str, state: Optional[str] = None, days: int = 30):
        api_key = self.get_api_key()
        if not api_key:
            self.log_telemetry(task_id, "SAM_SYNC", "FAILED", error="Missing API Key")
            return False

        today = datetime.datetime.now()
        since_date = (today - datetime.timedelta(days=days)).strftime('%m/%d/%Y')
        to_date = today.strftime('%m/%d/%Y')
        
        print(f"[GEORGE] Initiating SAM.gov Sync [State: {state if state else 'ALL'}]", flush=True)
        self.log_telemetry(task_id, "SAM_SYNC", "RUNNING", data={"state": state, "days": days})
        
        count = 0
        for naics in self.naics_codes:
            params = {
                "api_key": api_key,
                "ncode": naics,
                "postedFrom": since_date,
                "postedTo": to_date,
                "limit": 100
            }
            if state: params["state"] = state
            
            try:
                response = requests.get(self.api_endpoint, params=params)
                if response.status_code == 200:
                    data = response.json()
                    for opp_data in data.get('opportunitiesData', []):
                        try:
                            # Strict Pydantic Validation
                            opp = SAMOpportunity(**opp_data)
                            opp.naics = naics # Inject current naics
                            
                            # Persistence Logic
                            self.persist_opportunity(opp)
                            count += 1
                        except Exception as ve:
                            print(f"[WARN] Schema Validation Failed for notice {opp_data.get('noticeId')}: {ve}", flush=True)
                            continue
                elif response.status_code == 429:
                    print("[CRITICAL] SAM.gov Quota Exceeded. George is tripping the circuit breaker.", flush=True)
                    self.handle_error(task_id, Exception("API Rate Limit Exceeded (429)"))
                    return False
                else:
                    print(f"[WARN] API Error {response.status_code}", flush=True)
            except Exception as e:
                if self.handle_error(task_id, e):
                    return False
                    
        self.log_telemetry(task_id, "SAM_SYNC", "SUCCESS", data={"ingested": count})
        print(f"[GEORGE] Sync Complete. Ingested: {count} opportunities.", flush=True)
        return True

    def persist_opportunity(self, opp: SAMOpportunity):
        """Persists the validated opportunity into the institutional leads table."""
        db_path = "/app/database/sigma_leads.db" if os.path.exists("/app/main_app.py") else "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/database/sigma_leads.db"
        
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS sam_opportunities 
                         (notice_id TEXT PRIMARY KEY, title TEXT, naics TEXT, state TEXT, url TEXT, posted_date TEXT)''')
        
        cur.execute("INSERT OR IGNORE INTO sam_opportunities VALUES (?, ?, ?, ?, ?, ?)",
                     (opp.notice_id, opp.title, opp.naics, opp.state, opp.url, opp.posted_date))
        conn.commit()
        conn.close()
