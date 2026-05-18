-- SigmaFidelity™ Institutional Schema Re-Initialization
-- Standard: HWB-QMS-7.1 (Database Architecture)

CREATE TABLE IF NOT EXISTS "Milestones" (
    id SERIAL PRIMARY KEY,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    description TEXT,
    due_date DATE,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "agent_telemetry" (
    id SERIAL PRIMARY KEY,
    agent_id TEXT,
    task_id TEXT,
    action TEXT,
    status TEXT,
    data JSONB,
    error TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "agent_task_state" (
    task_id TEXT PRIMARY KEY,
    agent_id TEXT,
    current_step INTEGER,
    total_steps INTEGER,
    status TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "sigma_kb" (
    id SERIAL PRIMARY KEY,
    doc_id TEXT UNIQUE,
    content TEXT,
    search_vector tsvector,
    embedding float8[],
    metadata JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS sigma_kb_search_idx ON sigma_kb USING GIN(search_vector);
