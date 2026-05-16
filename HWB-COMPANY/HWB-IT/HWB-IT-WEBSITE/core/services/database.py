import psycopg2
import sqlite3
import re
import os
import datetime
from urllib.parse import urlparse
from psycopg2.extras import DictCursor

from contextlib import contextmanager

@contextmanager
def db_session(db_url):
    """
    SigmaFidelity™ Database Session Context Manager.
    Automatically handles connection setup, timezone sync, and teardown.
    """
    conn = get_db(db_url)
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def db_cursor(db_url):
    """
    SigmaFidelity™ Database Cursor Context Manager.
    Yields a cursor and automatically commits/closes the session.
    Handles both PostgreSQL (context-aware) and SQLite (manual) cursors.
    """
    with db_session(db_url) as conn:
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        finally:
            cur.close()

def get_db(db_url):
    """
    SigmaFidelity™ Unified Database Connector.
    Supports SQLite for local testing and PostgreSQL for institutional production.
    """
    try:
        parsed_url = urlparse(db_url)
        scheme = parsed_url.scheme
        
        if scheme == 'sqlite':
            db_path = parsed_url.path.lstrip('/')
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            def regexp(expr, item):
                if item is None: return False
                reg = re.compile(expr, re.IGNORECASE)
                return reg.search(str(item)) is not None
            conn.create_function("REGEXP", 2, regexp)
            return conn
        elif scheme in ['postgres', 'postgresql']:
            conn = psycopg2.connect(db_url, cursor_factory=DictCursor, connect_timeout=5)
            # Mandatory Institutional Timezone Sync
            with conn.cursor() as cur:
                cur.execute("SET TIME ZONE 'America/Chicago'")
            return conn
        else:
            raise ValueError(f"Unsupported database scheme: {scheme}")
    except Exception as e:
        print(f"[DB] Connection Failed: {e}", flush=True)
        raise e

def sync_db_sequences(db_url):
    """Ensures all Postgres sequences are aligned with current record counts."""
    try:
        conn = get_db(db_url)
        with conn.cursor() as cur:
            cur.execute("""
                DO $$ DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT table_name, column_name, column_default FROM information_schema.columns 
                              WHERE column_default LIKE 'nextval(%' AND table_schema = 'public') LOOP
                        EXECUTE 'SELECT setval(''' || substring(r.column_default from '''(.*)''' ) || ''', COALESCE(MAX(' || r.column_name || '), 1)) FROM "' || r.table_name || '"';
                    END LOOP;
                END $$;
            """)
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB] Sequence Sync Skipped: {e}", flush=True)
