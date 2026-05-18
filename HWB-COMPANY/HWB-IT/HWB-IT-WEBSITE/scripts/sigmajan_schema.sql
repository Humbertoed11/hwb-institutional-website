-- SigmaJan™ Institutional Database Schema (PostgreSQL)
-- Version 1.0
-- Master Deployment Script

-- 1. Users Table
CREATE TABLE IF NOT EXISTS Users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL
);

-- 2. Leads Table (Marketing Pipeline)
CREATE TABLE IF NOT EXISTS Leads (
    id SERIAL PRIMARY KEY,
    process_id VARCHAR(50) DEFAULT 'MKT-001',
    job_title VARCHAR(255),
    center_name VARCHAR(255),
    email VARCHAR(255),
    wage NUMERIC(10, 2),
    cleaning_hours NUMERIC(10, 2),
    calculated_waste NUMERIC(15, 2),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Chemicals Table (EHSQ Compliance)
CREATE TABLE IF NOT EXISTS Chemicals (
    id SERIAL PRIMARY KEY,
    process_id VARCHAR(50) DEFAULT 'SAFE-001',
    name VARCHAR(255) NOT NULL,
    product_id VARCHAR(100),
    hazard_level VARCHAR(50),
    intended_use TEXT,
    sds_link VARCHAR(500) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Milestones Table (Strategic Execution)
CREATE TABLE IF NOT EXISTS Milestones (
    id SERIAL PRIMARY KEY,
    category VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    description TEXT
);

-- 5. COPQ Table (Cost of Poor Quality Tracking)
CREATE TABLE IF NOT EXISTS COPQ (
    id SERIAL PRIMARY KEY,
    defect_type VARCHAR(255) NOT NULL,
    impact TEXT,
    status VARCHAR(50) DEFAULT 'OPEN'
);

-- 6. KPIVs Table (Key Process Input Variables)
CREATE TABLE IF NOT EXISTS KPIVs (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    value VARCHAR(255),
    target VARCHAR(255)
);

-- 7. Analytics Table
CREATE TABLE IF NOT EXISTS Analytics (
    id SERIAL PRIMARY KEY,
    tool_name VARCHAR(255) NOT NULL,
    result TEXT NOT NULL
);

-- 8. ActivityLog Table
CREATE TABLE IF NOT EXISTS ActivityLog (
    id SERIAL PRIMARY KEY,
    date DATE DEFAULT CURRENT_DATE,
    activity_name VARCHAR(255) NOT NULL,
    hours NUMERIC(5, 2) NOT NULL,
    category VARCHAR(100) DEFAULT 'Value-Add'
);

-- 9. Incidents Table
CREATE TABLE IF NOT EXISTS Incidents (
    id SERIAL PRIMARY KEY,
    date DATE DEFAULT CURRENT_DATE,
    description TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    severity VARCHAR(50) DEFAULT 'Low'
);

-- 10. Uptime Table
CREATE TABLE IF NOT EXISTS Uptime (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status INTEGER
);

-- 11. ClientActivities Table (CRM Engine)
CREATE TABLE IF NOT EXISTS ClientActivities (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL,
    activity_type VARCHAR(100) NOT NULL,
    description TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Note: Ensure initial admin user is created via the application layer logic.
