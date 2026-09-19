"""
SigmaFidelity™ Enterprise Database Connector & Connection Pool
Standard: HWB-QMS-7.6 Enterprise Architecture Standards
Custodians: George (Systems Architect) & Peter (Recovery Specialist)
"""

import os
import re
import sqlite3
import datetime
import threading
from urllib.parse import urlparse
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import DictCursor
from psycopg2.pool import ThreadedConnectionPool

# Thread-safe global pool registry mapped by database URL
_POOLS = {}
_POOLS_LOCK = threading.Lock()

MIN_POOL_CONNECTIONS = int(os.environ.get('DB_POOL_MIN', 2))
MAX_POOL_CONNECTIONS = int(os.environ.get('DB_POOL_MAX', 20))


class PooledConnection:
    """
    Transparent connection proxy that returns connections to the
    ThreadedConnectionPool upon close() rather than destroying the TCP socket.
    """
    def __init__(self, pool: ThreadedConnectionPool, raw_conn):
        self._pool = pool
        self._raw_conn = raw_conn
        self._closed = False

    def close(self):
        if not self._closed:
            self._closed = True
            try:
                # Reset dirty transactions before returning to pool
                if not self._raw_conn.closed and self._raw_conn.status == psycopg2.extensions.STATUS_IN_TRANSACTION:
                    self._raw_conn.rollback()
            except Exception:
                pass
            try:
                self._pool.putconn(self._raw_conn)
            except Exception as e:
                print(f"[POOL_WARN] putconn error: {e}", flush=True)

    def __enter__(self):
        return self._raw_conn.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._raw_conn.__exit__(exc_type, exc_val, exc_tb)

    def __getattr__(self, name):
        return getattr(self._raw_conn, name)

    @property
    def closed(self):
        return self._closed or self._raw_conn.closed


def get_connection_pool(db_url: str) -> ThreadedConnectionPool:
    """Retrieves or creates a ThreadedConnectionPool for the target Postgres database."""
    global _POOLS
    if db_url not in _POOLS:
        with _POOLS_LOCK:
            if db_url not in _POOLS:
                parsed = urlparse(db_url)
                print(f"[POOL_INIT] Creating ThreadedConnectionPool (min={MIN_POOL_CONNECTIONS}, max={MAX_POOL_CONNECTIONS}) for {parsed.hostname}", flush=True)
                _POOLS[db_url] = ThreadedConnectionPool(
                    minconn=MIN_POOL_CONNECTIONS,
                    maxconn=MAX_POOL_CONNECTIONS,
                    dsn=db_url,
                    cursor_factory=DictCursor,
                    connect_timeout=5
                )
    return _POOLS[db_url]


def get_db(db_url: str):
    """
    SigmaFidelity™ Unified Database Connector.
    Returns a pooled PostgreSQL connection or SQLite local connection.
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
            pool = get_connection_pool(db_url)
            raw_conn = pool.getconn()
            # Mandatory Institutional Timezone Sync
            with raw_conn.cursor() as cur:
                cur.execute("SET TIME ZONE 'America/Chicago'")
            return PooledConnection(pool, raw_conn)
            
        else:
            raise ValueError(f"Unsupported database scheme: {scheme}")
    except Exception as e:
        print(f"[DB] Connection Acquisition Failed: {e}", flush=True)
        raise e


@contextmanager
def db_session(db_url: str):
    """
    SigmaFidelity™ Database Session Context Manager.
    Automatically handles connection checkout, timezone sync, and return to pool.
    """
    conn = get_db(db_url)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def db_cursor(db_url: str):
    """
    SigmaFidelity™ Database Cursor Context Manager.
    Yields a cursor and automatically commits/closes the session back to the pool.
    """
    with db_session(db_url) as conn:
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        finally:
            cur.close()


def sync_db_sequences(db_url: str):
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


def get_pool_status(db_url: str = None) -> dict:
    """Returns empirical telemetry on active connection pools."""
    with _POOLS_LOCK:
        if db_url and db_url in _POOLS:
            pool = _POOLS[db_url]
            return {
                "active_pools": 1,
                "min_conn": pool.minconn,
                "max_conn": pool.maxconn,
                "closed": pool.closed
            }
        return {
            "active_pools": len(_POOLS),
            "pool_keys": [urlparse(k).hostname for k in _POOLS.keys()],
            "min_conn": MIN_POOL_CONNECTIONS,
            "max_conn": MAX_POOL_CONNECTIONS
        }
