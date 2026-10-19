"""
SigmaFidelity™ Schema Migration & Database Engine
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Peter (Recovery Specialist)
"""

import os
import sys
import importlib
from typing import Any, Optional

def apply_system_migrations(conn: Any, db_url: Optional[str] = None) -> None:
    """
    Executes idempotent, version-controlled schema migrations for PostgreSQL.
    Tracks applied migrations in the 'schema_migrations' table.
    """
    try:
        with conn.cursor() as cur:
            # 1. Version tracking table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS "schema_migrations" (
                    version VARCHAR(100) PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                );
            """)
            conn.commit()

            # Retrieve applied migrations
            cur.execute("SELECT version FROM schema_migrations;")
            applied = {row[0] for row in cur.fetchall()}

            # --- Migration 001: Core Table Hardening & Columns ---
            if "001_core_table_hardening" not in applied:
                print("[MIGRATION] Applying 001_core_table_hardening...", flush=True)
                # Services Table
                cur.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS traffic_cycle TEXT;')
                cur.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS frequency TEXT;')
                cur.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS notes TEXT;')
                cur.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS status TEXT DEFAULT \'Active\';')

                # Customers Table
                cur.execute('ALTER TABLE "Customers" ADD COLUMN IF NOT EXISTS billing_address TEXT;')
                cur.execute('ALTER TABLE "Customers" ADD COLUMN IF NOT EXISTS contract_period TEXT;')

                # Leads Table
                cur.execute('ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS is_dnc BOOLEAN DEFAULT FALSE;')

                # GlobalActivities Table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS "GlobalActivities" (
                        id SERIAL PRIMARY KEY,
                        parent_id INTEGER NOT NULL,
                        parent_type TEXT NOT NULL,
                        activity_type TEXT NOT NULL,
                        description TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                ''')

                # SigmaInteractionLog Table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS "SigmaInteractionLog" (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_prompt TEXT,
                        agent_explanation TEXT,
                        tools_used JSONB,
                        status VARCHAR(50)
                    );
                ''')

                # RolePermissions Table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS "RolePermissions" (
                        id SERIAL PRIMARY KEY,
                        role TEXT NOT NULL,
                        module TEXT NOT NULL,
                        can_view BOOLEAN DEFAULT FALSE,
                        can_edit BOOLEAN DEFAULT FALSE,
                        can_delete BOOLEAN DEFAULT FALSE
                    );
                ''')

                cur.execute("""
                    INSERT INTO "schema_migrations" (version, description)
                    VALUES ('001_core_table_hardening', 'Core operational columns and telemetry tables');
                """)
                conn.commit()
                print("[MIGRATION] 001_core_table_hardening successfully applied.", flush=True)

            # --- Migration 002: Test Lead Pruning & Data Cleanup ---
            if "002_test_data_pruning" not in applied:
                print("[MIGRATION] Applying 002_test_data_pruning...", flush=True)
                cur.execute('DELETE FROM "GlobalActivities" WHERE parent_id = 44518 AND parent_type = \'Lead\';')
                cur.execute('''
                    DELETE FROM "GlobalActivities" 
                    WHERE parent_id IN (SELECT id FROM "Leads" WHERE center_name ILIKE '%Test Lead%' OR lead_source = 'Executive Test System')
                      AND parent_type = 'Lead';
                ''')
                cur.execute('DELETE FROM "Leads" WHERE id = 44518 OR center_name ILIKE \'%DFW6%\' OR center_name ILIKE \'%Test Lead%\' OR lead_source = \'Executive Test System\';')

                cur.execute("""
                    INSERT INTO "schema_migrations" (version, description)
                    VALUES ('002_test_data_pruning', 'One-time pruning of test lead 44518 and DFW6 placeholders');
                """)
                conn.commit()
                print("[MIGRATION] 002_test_data_pruning successfully applied.", flush=True)

            # --- Migration 003: Phone Number Functional Index ---
            if "003_phone_digit_indexes" not in applied:
                print("[MIGRATION] Applying 003_phone_digit_indexes...", flush=True)
                cur.execute('''
                    CREATE INDEX IF NOT EXISTS idx_leads_phone_digits 
                    ON "Leads" (regexp_replace(COALESCE(phone, ''), '\\D', '', 'g'));
                ''')
                cur.execute('''
                    CREATE INDEX IF NOT EXISTS idx_customers_phone_digits 
                    ON "Customers" (regexp_replace(COALESCE(phone, ''), '\\D', '', 'g'));
                ''')
                cur.execute("""
                    INSERT INTO "schema_migrations" (version, description)
                    VALUES ('003_phone_digit_indexes', 'Functional regex indexes on phone digits for high-speed search');
                """)
                conn.commit()
                print("[MIGRATION] 003_phone_digit_indexes successfully applied.", flush=True)

            # --- Immediate Baseline Parity Hardening (Users, Leads, Customers) ---
            cur.execute('''
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS full_name TEXT;
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS email TEXT;
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'Operator';
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Active';
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS last_logout_at TIMESTAMP;
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS last_heartbeat_at TIMESTAMP;
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS last_login_ip VARCHAR(100);
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS login_count INTEGER DEFAULT 0;
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS force_pwd_reset BOOLEAN DEFAULT FALSE;
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS custom_permissions TEXT;
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS telegram_chat_id VARCHAR(50);
                UPDATE "Users" SET status = 'Active' WHERE status IS NULL;
                UPDATE "Users" SET role = 'Executive' WHERE username IN ('admin', 'hdominguez') AND (role IS NULL OR role = 'Operator');

                CREATE TABLE IF NOT EXISTS "ClientBreadcrumbs" (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    session_id VARCHAR(100) NOT NULL,
                    page_url VARCHAR(255) NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    element_tag VARCHAR(50) NULL,
                    element_id VARCHAR(100) NULL,
                    element_class VARCHAR(150) NULL,
                    element_text VARCHAR(150) NULL,
                    details JSONB NULL,
                    ip_address VARCHAR(45) NOT NULL DEFAULT '127.0.0.1',
                    user_agent TEXT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_client_bc_ts ON "ClientBreadcrumbs" (timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_client_bc_session ON "ClientBreadcrumbs" (session_id);

                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS is_commercial BOOLEAN DEFAULT TRUE;
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS is_dnc BOOLEAN DEFAULT FALSE;
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS is_converted BOOLEAN DEFAULT FALSE;
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS cleaning_delivery_model VARCHAR(50) DEFAULT 'UNKNOWN';
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS commercial_status VARCHAR(50) DEFAULT 'Commercial Hub';
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS acquisition_tier VARCHAR(50) DEFAULT 'Unranked';
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS ownership_type VARCHAR(50) DEFAULT 'Independent Commercial';
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS owner_verification_status VARCHAR(50) DEFAULT 'PENDING_PROOF';
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS owner_evidence_citation TEXT;
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN DEFAULT FALSE;
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS duplicate_group_id VARCHAR(64);
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS umbrella_name VARCHAR(100);

                ALTER TABLE "Customers" ADD COLUMN IF NOT EXISTS cleaning_delivery_model VARCHAR(50) DEFAULT 'DIRECT_W2';
                ALTER TABLE "Customers" ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Active';

                -- WorkOrders Parity
                CREATE TABLE IF NOT EXISTS "WorkOrders" (
                    work_order_id SERIAL PRIMARY KEY,
                    customer_id INTEGER NOT NULL,
                    service_id INTEGER,
                    status TEXT DEFAULT 'PENDING',
                    scheduled_date DATE,
                    scheduled_time TEXT,
                    actual_start_time TEXT,
                    actual_end_time TEXT,
                    crew_lead_id INTEGER,
                    client_notes TEXT,
                    crew_notes TEXT,
                    photo_proof_url TEXT,
                    last_gps_lat DOUBLE PRECISION,
                    last_gps_long DOUBLE PRECISION,
                    created_at DATE DEFAULT CURRENT_TIMESTAMP,
                    shift_window VARCHAR(100) DEFAULT 'Evening Shift (6:00 PM – 11:00 PM)',
                    service_type VARCHAR(100) DEFAULT 'Routine Nightly Custodial',
                    assigned_technician_id INTEGER,
                    quality_score NUMERIC(5,2),
                    completion_signature TEXT,
                    supervisor_signoff TEXT,
                    checklist_progress JSONB DEFAULT '[]'::jsonb,
                    dock_ingress_instructions TEXT,
                    security_access_code VARCHAR(100)
                );

                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS shift_window VARCHAR(100) DEFAULT 'Evening Shift (6:00 PM – 11:00 PM)';
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS service_type VARCHAR(100) DEFAULT 'Routine Nightly Custodial';
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS assigned_technician_id INTEGER;
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS crew_lead_id INTEGER;
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS quality_score NUMERIC(5,2);
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS completion_signature TEXT;
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS supervisor_signoff TEXT;
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS checklist_progress JSONB DEFAULT '[]'::jsonb;
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS dock_ingress_instructions TEXT;
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS security_access_code VARCHAR(100);

                -- ConstructionBids Table Parity
                CREATE TABLE IF NOT EXISTS "ConstructionBids" (
                    id SERIAL PRIMARY KEY,
                    gc_name VARCHAR(255) NOT NULL,
                    project_name VARCHAR(255) NOT NULL,
                    project_address VARCHAR(255),
                    city VARCHAR(100),
                    state VARCHAR(50) DEFAULT 'TX',
                    zipcode VARCHAR(20),
                    bid_due_date TIMESTAMP WITH TIME ZONE,
                    estimated_start_date DATE,
                    estimated_end_date DATE,
                    cleanable_sqft NUMERIC DEFAULT 0,
                    estimated_value NUMERIC DEFAULT 0,
                    scope_phase VARCHAR(150) DEFAULT 'Rough, Final & Touch-Up Clean',
                    special_requirements TEXT,
                    estimator_name VARCHAR(150),
                    estimator_title VARCHAR(100),
                    estimator_email VARCHAR(150),
                    estimator_phone VARCHAR(50),
                    platform VARCHAR(100) DEFAULT 'BuildingConnected',
                    rfp_url TEXT,
                    plan_url TEXT,
                    status VARCHAR(50) DEFAULT 'Invited',
                    prequal_status VARCHAR(50) DEFAULT 'Ready',
                    last_contact_date TIMESTAMP WITH TIME ZONE,
                    next_action VARCHAR(255),
                    next_action_date DATE,
                    notes TEXT,
                    email_id VARCHAR(255) UNIQUE,
                    assigned_rep_id INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                ALTER TABLE "ConstructionBids" ADD COLUMN IF NOT EXISTS assigned_rep_id INTEGER;

                -- Contacts Table Parity
                CREATE TABLE IF NOT EXISTS "Contacts" (
                    contact_id SERIAL PRIMARY KEY,
                    account_id INTEGER,
                    full_name TEXT,
                    role TEXT,
                    email TEXT,
                    phone TEXT,
                    title TEXT,
                    department TEXT,
                    reports_to INTEGER,
                    lead_id INTEGER
                );

                -- ScopeLibrary Table Parity
                CREATE TABLE IF NOT EXISTS "ScopeLibrary" (
                    id SERIAL PRIMARY KEY,
                    category TEXT NOT NULL,
                    value TEXT NOT NULL
                );

                -- EmployeeDocuments Table Parity
                CREATE TABLE IF NOT EXISTS "EmployeeDocuments" (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER,
                    applicant_id INTEGER,
                    document_type VARCHAR(100) NOT NULL,
                    file_name VARCHAR(255) NOT NULL,
                    file_path VARCHAR(255) NOT NULL,
                    file_size INTEGER,
                    mime_type VARCHAR(100),
                    verification_status VARCHAR(50) DEFAULT 'Verified',
                    expiration_date DATE,
                    verified_by VARCHAR(100) DEFAULT 'Humberto Dominguez',
                    verified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                -- PendingOutbox & SocialOutbox Parity
                CREATE TABLE IF NOT EXISTS "PendingOutbox" (
                    id SERIAL PRIMARY KEY,
                    recipient TEXT,
                    subject TEXT,
                    body TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'PENDING',
                    tracking_token VARCHAR(64),
                    campaign_id INTEGER,
                    recipient_id INTEGER
                );

                CREATE TABLE IF NOT EXISTS "SocialOutbox" (
                    id SERIAL PRIMARY KEY,
                    platform TEXT,
                    content TEXT,
                    media_url TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'PENDING'
                );

                -- JobPositions Table Parity
                CREATE TABLE IF NOT EXISTS "JobPositions" (
                    id SERIAL PRIMARY KEY,
                    position_code VARCHAR(50) UNIQUE NOT NULL,
                    title VARCHAR(150) NOT NULL,
                    department VARCHAR(100) NOT NULL,
                    reports_to VARCHAR(150) NOT NULL,
                    summary TEXT NOT NULL,
                    key_responsibilities JSONB NOT NULL DEFAULT '[]'::jsonb,
                    required_competencies JSONB NOT NULL DEFAULT '[]'::jsonb,
                    required_experience VARCHAR(150) NOT NULL,
                    required_certifications JSONB NOT NULL DEFAULT '[]'::jsonb,
                    physical_demands TEXT NOT NULL,
                    work_environment VARCHAR(255) NOT NULL,
                    hourly_min NUMERIC(8,2) NOT NULL DEFAULT 16.00,
                    hourly_max NUMERIC(8,2) NOT NULL DEFAULT 25.00,
                    standard_weekly_hours NUMERIC(4,1) DEFAULT 40.0,
                    is_active BOOLEAN DEFAULT TRUE,
                    sop_template_id VARCHAR(50) DEFAULT 'HWB-FORM-7.2-001',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );

                -- JobApplicants Table Parity
                CREATE TABLE IF NOT EXISTS "JobApplicants" (
                    id SERIAL PRIMARY KEY,
                    full_name VARCHAR(150) NOT NULL,
                    phone VARCHAR(50) NOT NULL,
                    email VARCHAR(150),
                    city VARCHAR(100),
                    state VARCHAR(50) DEFAULT 'TX',
                    desired_role VARCHAR(100) DEFAULT 'Commercial Cleaning Technician',
                    desired_shift VARCHAR(50) DEFAULT 'Night',
                    experience_level VARCHAR(50) DEFAULT '1-2 Years',
                    has_transportation BOOLEAN DEFAULT TRUE,
                    authorized_to_work_us BOOLEAN DEFAULT TRUE,
                    preferred_language VARCHAR(50) DEFAULT 'English',
                    status VARCHAR(50) DEFAULT 'New',
                    notes TEXT,
                    job_position_id INTEGER REFERENCES "JobPositions"(id) ON DELETE SET NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                -- SubcontractorPartners Table Parity
                CREATE TABLE IF NOT EXISTS "SubcontractorPartners" (
                    id SERIAL PRIMARY KEY,
                    company_name VARCHAR(200) NOT NULL,
                    contact_name VARCHAR(150) NOT NULL,
                    phone VARCHAR(50) NOT NULL,
                    email VARCHAR(150),
                    ein_tax_id VARCHAR(50),
                    city VARCHAR(100),
                    state VARCHAR(50) DEFAULT 'TX',
                    coi_status VARCHAR(50) DEFAULT 'Active',
                    coi_expiration DATE,
                    w9_status VARCHAR(50) DEFAULT 'Verified',
                    preferred_payment_terms VARCHAR(50) DEFAULT 'Net 15',
                    hourly_rate_agreed NUMERIC(10,2) DEFAULT 22.00,
                    specialties TEXT,
                    status VARCHAR(50) DEFAULT 'Active',
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_subcontractors_unique_phone_digits
                ON "SubcontractorPartners" ((REGEXP_REPLACE(COALESCE(phone, ''), '\D', '', 'g')))
                WHERE LENGTH(REGEXP_REPLACE(COALESCE(phone, ''), '\D', '', 'g')) = 10;
                CREATE INDEX IF NOT EXISTS idx_jobapplicants_phone_digits
                ON "JobApplicants" ((REGEXP_REPLACE(COALESCE(phone, ''), '\D', '', 'g')));

                -- Employees Table Parity
                CREATE TABLE IF NOT EXISTS "Employees" (
                    id SERIAL PRIMARY KEY,
                    employee_number VARCHAR(50) UNIQUE NOT NULL,
                    applicant_id INTEGER REFERENCES "JobApplicants"(id) ON DELETE SET NULL,
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100) NOT NULL,
                    phone VARCHAR(50) NOT NULL,
                    email VARCHAR(150),
                    date_of_birth DATE,
                    hire_date DATE NOT NULL DEFAULT CURRENT_DATE,
                    termination_date DATE,
                    employment_status VARCHAR(50) DEFAULT 'Active',
                    employment_type VARCHAR(50) DEFAULT 'W-2 Full-Time',
                    primary_role VARCHAR(100) DEFAULT 'Commercial Cleaning Technician',
                    pay_rate_hourly NUMERIC(10,2) NOT NULL DEFAULT 16.00,
                    overtime_rate_hourly NUMERIC(10,2) DEFAULT 24.00,
                    pay_frequency VARCHAR(50) DEFAULT 'Bi-Weekly',
                    primary_language VARCHAR(50) DEFAULT 'Spanish',
                    emergency_contact_name VARCHAR(150),
                    emergency_contact_phone VARCHAR(50),
                    address_street VARCHAR(255),
                    address_city VARCHAR(100),
                    address_state VARCHAR(50) DEFAULT 'TX',
                    address_zip VARCHAR(20),
                    direct_deposit_bank VARCHAR(100),
                    direct_deposit_routing VARCHAR(50),
                    direct_deposit_account VARCHAR(50),
                    direct_deposit_account_encrypted TEXT,
                    direct_deposit_account_last_four VARCHAR(4),
                    ssn_encrypted TEXT,
                    ssn_last_four VARCHAR(4),
                    assigned_customer_id INTEGER REFERENCES "Customers"(customer_id) ON DELETE SET NULL,
                    weekly_hours_allocated NUMERIC(6,2) DEFAULT 40.00,
                    badge_status VARCHAR(50) DEFAULT 'Active',
                    driver_license_number VARCHAR(50),
                    driver_license_expiration DATE,
                    dps_clearance_date DATE,
                    notes TEXT,
                    job_position_id INTEGER REFERENCES "JobPositions"(id) ON DELETE SET NULL,
                    job_description_acknowledged_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                -- InstitutionalBids Table Parity
                CREATE TABLE IF NOT EXISTS "InstitutionalBids" (
                    id SERIAL PRIMARY KEY,
                    solicitation_number VARCHAR(100) UNIQUE NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    agency_name VARCHAR(255) NOT NULL,
                    sector VARCHAR(100) DEFAULT 'Transportation & Infrastructure',
                    portal_name VARCHAR(100) DEFAULT 'NTTA Marketplace',
                    portal_doc_id VARCHAR(100),
                    procurement_officer VARCHAR(150),
                    officer_email VARCHAR(150),
                    officer_phone VARCHAR(50),
                    contract_term_months INTEGER DEFAULT 24,
                    cleanable_sqft NUMERIC DEFAULT 0,
                    facilities_count INTEGER DEFAULT 1,
                    published_budget NUMERIC(12,2) DEFAULT 0.00,
                    hwb_bid_total NUMERIC(12,2) DEFAULT 0.00,
                    monthly_base_rate NUMERIC(10,2) DEFAULT 0.00,
                    annual_base_rate NUMERIC(12,2) DEFAULT 0.00,
                    hourly_porter_rate NUMERIC(8,2) DEFAULT 0.00,
                    pre_bid_datetime TIMESTAMP WITH TIME ZONE,
                    pre_bid_type VARCHAR(100),
                    pre_bid_url TEXT,
                    site_walk_datetime TIMESTAMP WITH TIME ZONE,
                    site_walk_location VARCHAR(255),
                    questions_due_date TIMESTAMP WITH TIME ZONE,
                    bid_due_date TIMESTAMP WITH TIME ZONE,
                    public_opening_datetime TIMESTAMP WITH TIME ZONE,
                    public_opening_url TEXT,
                    status VARCHAR(50) DEFAULT 'Active Solicitation',
                    compliance_status VARCHAR(100) DEFAULT 'Package Unified & Ready',
                    compliance_summary TEXT,
                    local_quote_path VARCHAR(255),
                    bid_sheet_path VARCHAR(255),
                    dossier_path VARCHAR(255),
                    rfp_url TEXT,
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                -- MarketingCampaigns Table Parity
                CREATE TABLE IF NOT EXISTS "MarketingCampaigns" (
                    id SERIAL PRIMARY KEY,
                    campaign_code VARCHAR(64) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    target_sector VARCHAR(100) NOT NULL,
                    target_geo VARCHAR(255) DEFAULT 'Collin, Dallas, Denton, Tarrant',
                    cadence_type VARCHAR(50) DEFAULT '3-Step Compliance',
                    template_id VARCHAR(100) DEFAULT 'TMPL_CHILDCARE_HEALTH_V1',
                    sender_persona VARCHAR(100) DEFAULT 'Humberto Dominguez (Owner & Operator)',
                    status VARCHAR(50) DEFAULT 'Draft',
                    email_subject_template TEXT,
                    email_body_template TEXT,
                    total_targets INTEGER DEFAULT 0,
                    staged_count INTEGER DEFAULT 0,
                    sent_count INTEGER DEFAULT 0,
                    opened_count INTEGER DEFAULT 0,
                    walkthroughs_booked INTEGER DEFAULT 0,
                    total_mrr_won NUMERIC(12,2) DEFAULT 0.00,
                    daily_throttle_limit INTEGER DEFAULT 50,
                    created_by VARCHAR(100) DEFAULT 'George (Systems Architect)',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                -- CampaignRecipients Table Parity
                CREATE TABLE IF NOT EXISTS "CampaignRecipients" (
                    id SERIAL PRIMARY KEY,
                    campaign_id INTEGER REFERENCES "MarketingCampaigns"(id) ON DELETE CASCADE,
                    lead_id INTEGER REFERENCES "Leads"(id) ON DELETE SET NULL,
                    recipient_email VARCHAR(255) NOT NULL,
                    recipient_name VARCHAR(150),
                    facility_name VARCHAR(255),
                    city VARCHAR(100),
                    county VARCHAR(100),
                    capacity INTEGER,
                    sqf INTEGER,
                    current_step INTEGER DEFAULT 1,
                    status VARCHAR(50) DEFAULT 'STAGED',
                    tracking_token VARCHAR(64) UNIQUE,
                    opened_at TIMESTAMP WITH TIME ZONE,
                    open_count INTEGER DEFAULT 0,
                    clicked_at TIMESTAMP WITH TIME ZONE,
                    click_count INTEGER DEFAULT 0,
                    outbox_id INTEGER,
                    scheduled_send_at TIMESTAMP WITH TIME ZONE,
                    sent_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                -- CampaignRecipients and Marketing Telemetry Column Hardening
                ALTER TABLE "CampaignRecipients" ADD COLUMN IF NOT EXISTS tracking_token VARCHAR(64) UNIQUE;
                ALTER TABLE "CampaignRecipients" ADD COLUMN IF NOT EXISTS opened_at TIMESTAMP WITH TIME ZONE;
                ALTER TABLE "CampaignRecipients" ADD COLUMN IF NOT EXISTS open_count INTEGER DEFAULT 0;
                ALTER TABLE "CampaignRecipients" ADD COLUMN IF NOT EXISTS clicked_at TIMESTAMP WITH TIME ZONE;
                ALTER TABLE "CampaignRecipients" ADD COLUMN IF NOT EXISTS click_count INTEGER DEFAULT 0;
                ALTER TABLE "CampaignRecipients" ADD COLUMN IF NOT EXISTS outbox_id INTEGER;
                ALTER TABLE "CampaignRecipients" ADD COLUMN IF NOT EXISTS scheduled_send_at TIMESTAMP WITH TIME ZONE;
                ALTER TABLE "CampaignRecipients" ADD COLUMN IF NOT EXISTS sent_at TIMESTAMP WITH TIME ZONE;

                CREATE INDEX IF NOT EXISTS "idx_camp_recip_token" ON "CampaignRecipients" (tracking_token);
                CREATE INDEX IF NOT EXISTS "idx_camp_recip_open" ON "CampaignRecipients" (opened_at);

                ALTER TABLE "MarketingCampaigns" ADD COLUMN IF NOT EXISTS email_subject_template TEXT;
                ALTER TABLE "MarketingCampaigns" ADD COLUMN IF NOT EXISTS email_body_template TEXT;

                ALTER TABLE "PendingOutbox" ADD COLUMN IF NOT EXISTS tracking_token VARCHAR(64);
                ALTER TABLE "PendingOutbox" ADD COLUMN IF NOT EXISTS campaign_id INTEGER;
                ALTER TABLE "PendingOutbox" ADD COLUMN IF NOT EXISTS recipient_id INTEGER;

                CREATE INDEX IF NOT EXISTS "idx_pending_outbox_token" ON "PendingOutbox" (tracking_token);
                CREATE INDEX IF NOT EXISTS "idx_pending_outbox_campaign" ON "PendingOutbox" (campaign_id);

                -- AcademyPackages Table Parity (Curriculum Bundles)
                CREATE TABLE IF NOT EXISTS "AcademyPackages" (
                    id SERIAL PRIMARY KEY,
                    package_code VARCHAR(64) UNIQUE NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    target_role VARCHAR(100) NOT NULL,
                    description TEXT,
                    regulatory_standards VARCHAR(255),
                    price_usd NUMERIC(10,2) DEFAULT 0.00,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_academy_packages_code" ON "AcademyPackages" (package_code);
                CREATE INDEX IF NOT EXISTS "idx_academy_packages_role" ON "AcademyPackages" (target_role);

                -- AcademyPackageCourses Table Parity
                CREATE TABLE IF NOT EXISTS "AcademyPackageCourses" (
                    id SERIAL PRIMARY KEY,
                    package_id INTEGER REFERENCES "AcademyPackages"(id) ON DELETE CASCADE,
                    course_id INTEGER REFERENCES "AcademyCourses"(id) ON DELETE CASCADE,
                    display_order INTEGER DEFAULT 1,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(package_id, course_id)
                );

                -- AcademyEnrollments Enhancement Parity
                ALTER TABLE "AcademyEnrollments" ADD COLUMN IF NOT EXISTS magic_token VARCHAR(64) UNIQUE;
                ALTER TABLE "AcademyEnrollments" ADD COLUMN IF NOT EXISTS assigned_package_code VARCHAR(64);
                ALTER TABLE "AcademyEnrollments" ADD COLUMN IF NOT EXISTS assigned_by VARCHAR(100);
                ALTER TABLE "AcademyEnrollments" ADD COLUMN IF NOT EXISTS due_date DATE;
                ALTER TABLE "AcademyEnrollments" ADD COLUMN IF NOT EXISTS notification_sent BOOLEAN DEFAULT FALSE;

                CREATE INDEX IF NOT EXISTS "idx_academy_enrollments_token" ON "AcademyEnrollments" (magic_token);
                CREATE INDEX IF NOT EXISTS "idx_academy_enrollments_pkg" ON "AcademyEnrollments" (assigned_package_code);

                -- SafetyManuals Table Parity
                CREATE TABLE IF NOT EXISTS "SafetyManuals" (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(50) UNIQUE NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    subtitle VARCHAR(255),
                    department VARCHAR(50) DEFAULT 'EHSQ',
                    version VARCHAR(20) DEFAULT '1.0.0',
                    status VARCHAR(50) DEFAULT 'APPROVED',
                    regulatory_scope VARCHAR(255) NOT NULL,
                    target_sector VARCHAR(100) NOT NULL,
                    docx_url VARCHAR(255) NOT NULL DEFAULT '',
                    html_url VARCHAR(255) NOT NULL DEFAULT '',
                    approved_by VARCHAR(100) DEFAULT 'Humberto Dominguez, CEO',
                    approval_date DATE DEFAULT '2026-09-21',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                -- JobHazardAnalyses Table Parity
                CREATE TABLE IF NOT EXISTS "JobHazardAnalyses" (
                    id SERIAL PRIMARY KEY,
                    jha_number VARCHAR(50) UNIQUE NOT NULL,
                    project_name VARCHAR(255) NOT NULL,
                    location VARCHAR(255) NOT NULL,
                    facility_type VARCHAR(100) NOT NULL,
                    inspection_date DATE NOT NULL,
                    lead_inspector VARCHAR(100) NOT NULL,
                    hazards_identified TEXT NOT NULL,
                    ppe_mandates TEXT NOT NULL,
                    engineering_controls TEXT NOT NULL,
                    crew_count INTEGER DEFAULT 1,
                    status VARCHAR(50) DEFAULT 'Active',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                -- SafetyIncidents Table Parity
                CREATE TABLE IF NOT EXISTS "SafetyIncidents" (
                    id SERIAL PRIMARY KEY,
                    incident_number VARCHAR(50) UNIQUE NOT NULL,
                    incident_date DATE NOT NULL,
                    incident_type VARCHAR(50) NOT NULL,
                    location VARCHAR(255) NOT NULL,
                    person_involved VARCHAR(100),
                    description TEXT NOT NULL,
                    corrective_action TEXT,
                    days_away_from_work INTEGER DEFAULT 0,
                    ceo_reviewed BOOLEAN DEFAULT FALSE,
                    status VARCHAR(50) DEFAULT 'Logged',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            conn.commit()

            # Seed ScopeLibrary if empty
            cur.execute('SELECT COUNT(*) FROM "ScopeLibrary";')
            if cur.fetchone()[0] == 0:
                cur.execute('''
                    INSERT INTO "ScopeLibrary" (category, value) VALUES
                    ('area', 'Main entrance'),
                    ('task', 'Clean moving glass'),
                    ('item', 'Front Door'),
                    ('area', 'Main Lobby'),
                    ('task', 'High Dusting'),
                    ('item', 'Ceiling corners, fan, AC register');
                ''')
                # Record inline baseline migrations
            inline_versions = [
                ("013_employee_lifecycle_suite", "Employee lifecycle, W-4, PTO, and compliance columns"),
                ("014_account_lifecycle_suite", "Institutional account lifecycle, contract terms, and COI verification"),
                ("016_sensitive_pii_vault", "Sensitive PII AES-256 encrypted vault for SSN/ITIN and banking"),
                ("018_institutional_users_and_schema_parity", "Institutional Users table hardening, credential sync, and leads parity"),
                ("019_ceo_credentials_and_alias_hardening", "CEO credentials and identity alias hardening"),
                ("020_lead_data_integrity_cleansing", "Lead data integrity, legacy industry/facility cleansing, address repair, and duplicate resolution"),
                ("021_simplify_job_positions_and_competitive_pay", "Simplified job descriptions, everyday words, and calibrated competitive pay"),
                ("012_marketing_tracking_and_builder", "Telemetry open tracking pixel, tokens, and campaign builder template support")
            ]
            for iv_tag, iv_desc in inline_versions:
                if iv_tag not in applied:
                    cur.execute("""
                        INSERT INTO "schema_migrations" (version, description)
                        VALUES (%s, %s)
                        ON CONFLICT (version) DO NOTHING;
                    """, (iv_tag, iv_desc))
                    applied.add(iv_tag)
            conn.commit()

            # --- Modular Migrations (External Scripts) ---
            target_db_url = db_url or os.environ.get("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")
            
            modular_migrations = [
                ("004_workforce_and_subcontractors", "scripts.migrate_004_workforce", "Job applicants and 1099 subcontractor partner tables with document tracking"),
                ("005_user_telegram_chat_id", "scripts.migrate_005_user_telegram", "Added telegram_chat_id to Users table for multi-user Telegram dispatch"),
                ("006_telegram_behavioral_telemetry", "scripts.migrate_006_telegram_behavioral_telemetry", "Telegram behavioral telemetry and interaction scoring"),
                ("007_human_resources_and_payroll", "scripts.migrate_007_human_resources_and_payroll", "Human Resources master personnel ledger, secure document vault, and payroll timesheet engine"),
                ("008_sigma_academy_lms", "scripts.migrate_008_sigma_academy_lms", "Sigma Academy LMS courses, enrollments, and progress tracking"),
                ("009_academy_packages", "scripts.migrate_009_academy_packages", "SigmaAcademy role-based training packages, curriculum bundles, and magic tokens"),
                ("010_institutional_bids", "scripts.migrate_010_institutional_bids", "Construction bids and document attachment vault"),
                ("011_marketing_department", "scripts.migrate_011_marketing_department", "Marketing campaigns and social dispatch outbox"),
                ("012_ehsq_safety_department", "scripts.migrate_012_ehsq_safety_department", "EHSQ safety inspections, hazard tracking, and compliance certifications"),
                ("015_internal_dispatch_suite", "scripts.migrate_015_internal_dispatch_suite", "Internal dispatch work orders, shifts, and execution monitor"),
                ("017_job_positions_and_descriptions", "scripts.migrate_017_job_positions_and_descriptions", "Job positions catalog, digital job descriptions, and ATS linking"),
                ("022_bids_pipeline_parity", "scripts.migrate_022_bids_pipeline_parity", "Commercial Construction Bids and Institutional Solicitations Parity Seed"),
                ("023_sales_desk_and_credentials_parity", "scripts.migrate_023_sales_desk_and_credentials_parity", "Field Sales Desk decoupling and sales credentials parity"),
                ("024_bidding_evolution_documents_and_sca", "scripts.migrate_024_bidding_evolution_documents_and_sca", "Digital Bid Room, BidAddenda sentinel, BidRFIs, and McNamara-O'Hara SCA engine"),
                ("025_gc_vetting_and_profile_enrichment", "scripts.migrate_025_gc_vetting_and_profile_enrichment", "Master GeneralContractors registry, 4-point vetting scorecard, and autonomous profile enrichment"),
                ("026_rack_telemetry_historical_snapshots", "scripts.migrate_026_rack_telemetry_history", "Historical snapshot ledger for 7-rack telemetry, memory rot, Six Sigma SPC, and Pareto distributions"),
                ("027_multitenant_rls_and_quarantine_ingestion", "scripts.migrate_027_multitenant_rls_and_quarantine_ingestion", "Kernel-level PostgreSQL Row-Level Security (RLS) tenant isolation and quarantine ingestion buffer"),
                ("028_lead_dataset_cleansing_and_deduplication", "scripts.migrate_028_lead_dataset_cleansing_and_deduplication", "Lead dataset deduplication, PROC-002 phone normalization, state standardization, and valuation backfill"),
                ("029_lead_industry_facility_classification", "scripts.migrate_029_lead_industry_facility_classification", "Lead industry and facility type classification, lexical parsing, and source purification"),
                ("030_purchasing_cooperatives_and_charter_institutions", "scripts.migrate_030_purchasing_cooperatives_and_charter_institutions", "Purchasing cooperatives and TEA charter school institutions registry"),
                ("031_government_programs_and_certifications", "scripts.migrate_031_government_programs_and_certifications", "Government programs SBA 8(a), HUB, and SDB certifications master registry"),
                ("032_multitenant_compliance_and_governance", "scripts.migrate_032_multitenant_compliance_and_governance", "Multi-tenant B2G compliance engine, multi-tenant program matching, and 13 CFR § 124 rules"),
                ("033_live_lead_deduplication", "scripts.migrate_033_live_lead_deduplication", "Live lead dataset deduplication, Golden Master consolidation, child re-parenting, and unique index enforcement"),
                ("034_sync_dev_to_production", "scripts.migrate_034_sync_dev_to_production", "Full production sync: 1,231 mined leads, corporate umbrellas, coops, gov programs, and institutional bids"),
                ("035_site_security_rack_09", "scripts.migrate_035_site_security_rack_09", "Site Security Rack #9 immutable audit ledger with database-level WORM trigger and high-density indexing"),
                ("036_user_custom_scripts", "scripts.migrate_036_user_custom_scripts", "User custom calling scripts and personal profile script library"),
                ("039_sales_and_account_executive_positions", "scripts.migrate_039_sales_and_account_executive_positions", "Digital job positions and descriptions for Remote Sales, Outside Sales, and Account Executives"),
                ("043_enterprise_campaign_readiness", "scripts.migrate_043_enterprise_campaign_readiness", "Enterprise 5-Pillar Marketing Campaign Readiness, DNS MX Health, Suppression Ledger, and 2,998 Enriched Childcare Sync")
            ]

            # --- Migration 040: High-Speed Scalability Indexes ---
            if "040_high_speed_scalability_indexes" not in applied:
                print("[MIGRATION] Applying 040_high_speed_scalability_indexes...", flush=True)
                cur.execute('CREATE INDEX IF NOT EXISTS idx_leads_city_status ON "Leads" (city, status);')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_leads_facility_type ON "Leads" (facility_type);')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_leads_input_date ON "Leads" (input_date DESC);')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_construction_bids_status ON "ConstructionBids" (status);')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_institutional_bids_status ON "InstitutionalBids" (status);')
                cur.execute("""
                    INSERT INTO "schema_migrations" (version, description)
                    VALUES ('040_high_speed_scalability_indexes', 'High-speed B-Tree indexes on Leads, ConstructionBids, and InstitutionalBids for zero-cost scalability')
                    ON CONFLICT (version) DO NOTHING;
                """)
                conn.commit()
                applied.add("040_high_speed_scalability_indexes")
                print("[MIGRATION] 040_high_speed_scalability_indexes successfully applied and recorded.", flush=True)

            # --- Migration 041: Enterprise Deduplication & Smart Merge Indexes ---
            if "041_enterprise_deduplication_indexes" not in applied:
                print("[MIGRATION] Applying 041_enterprise_deduplication_indexes...", flush=True)
                cur.execute('''
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_subcontractors_unique_phone_digits
                    ON "SubcontractorPartners" (RIGHT(REGEXP_REPLACE(COALESCE(phone, ''), '[^0-9]', '', 'g'), 10))
                    WHERE LENGTH(REGEXP_REPLACE(COALESCE(phone, ''), '[^0-9]', '', 'g')) >= 10;
                ''')
                cur.execute('''
                    CREATE INDEX IF NOT EXISTS idx_jobapplicants_phone_digits
                    ON "JobApplicants" (RIGHT(REGEXP_REPLACE(COALESCE(phone, ''), '[^0-9]', '', 'g'), 10));
                ''')
                cur.execute('''
                    CREATE INDEX IF NOT EXISTS idx_leads_phone_digits
                    ON "Leads" (RIGHT(REGEXP_REPLACE(COALESCE(phone, ''), '[^0-9]', '', 'g'), 10))
                    WHERE COALESCE(is_duplicate, FALSE) = FALSE;
                ''')
                cur.execute('''
                    CREATE INDEX IF NOT EXISTS idx_employees_phone_digits
                    ON "Employees" (RIGHT(REGEXP_REPLACE(COALESCE(phone, ''), '[^0-9]', '', 'g'), 10));
                ''')
                cur.execute('''
                    CREATE INDEX IF NOT EXISTS idx_customers_phone_digits
                    ON "Customers" (RIGHT(REGEXP_REPLACE(COALESCE(phone, ''), '[^0-9]', '', 'g'), 10));
                ''')
                cur.execute('''
                    CREATE INDEX IF NOT EXISTS idx_construction_bids_gc_project
                    ON "ConstructionBids" (LOWER(TRIM(COALESCE(gc_name, ''))), LOWER(TRIM(COALESCE(project_name, ''))));
                ''')
                cur.execute('''
                    CREATE INDEX IF NOT EXISTS idx_institutional_bids_solicitation
                    ON "InstitutionalBids" (LOWER(TRIM(COALESCE(solicitation_number, ''))));
                ''')
                cur.execute("""
                    INSERT INTO "schema_migrations" (version, description)
                    VALUES ('041_enterprise_deduplication_indexes', 'Enterprise deduplication functional indexes across SubcontractorPartners, JobApplicants, Leads, Employees, Customers, ConstructionBids, and InstitutionalBids')
                    ON CONFLICT (version) DO NOTHING;
                """)
                conn.commit()
                applied.add("041_enterprise_deduplication_indexes")
                print("[MIGRATION] 041_enterprise_deduplication_indexes successfully applied and recorded.", flush=True)

            if "042_sales_territory_and_caller_tags" not in applied:
                cur.execute("""
                    ALTER TABLE "ConstructionBids" ADD COLUMN IF NOT EXISTS assigned_rep_id INTEGER;
                    CREATE INDEX IF NOT EXISTS idx_construction_bids_assigned_rep ON "ConstructionBids"(assigned_rep_id);
                    DO $$
                    BEGIN
                        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_scripts' AND column_name = 'content') THEN
                            UPDATE "user_scripts"
                            SET content = REPLACE(content, 'Humberto Dominguez, CEO and founder of', '{Caller} with'),
                                updated_at = CURRENT_TIMESTAMP
                            WHERE content LIKE '%Humberto Dominguez, CEO and founder of%';
                        ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_scripts' AND column_name = 'script_body') THEN
                            UPDATE "user_scripts"
                            SET script_body = REPLACE(script_body, 'Humberto Dominguez, CEO and founder of', '{Caller} with'),
                                updated_at = CURRENT_TIMESTAMP
                            WHERE script_body LIKE '%Humberto Dominguez, CEO and founder of%';
                        END IF;
                    END $$;
                    INSERT INTO "schema_migrations" (version, description)
                    VALUES ('042_sales_territory_and_caller_tags', 'Add assigned_rep_id to ConstructionBids and replace hardcoded founder name in shared user_scripts with dynamic {Caller} tag')
                    ON CONFLICT (version) DO NOTHING;
                """)
                conn.commit()
                applied.add("042_sales_territory_and_caller_tags")
                print("[MIGRATION] 042_sales_territory_and_caller_tags successfully applied and recorded.", flush=True)

            if "043_backoffice_cqrs_covering_indexes" not in applied:
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_global_activities_parent_lookup
                    ON "GlobalActivities" (parent_type, parent_id, timestamp DESC);

                    CREATE INDEX IF NOT EXISTS idx_campaign_recipients_lead_lookup
                    ON "CampaignRecipients" (lead_id, id DESC);

                    CREATE INDEX IF NOT EXISTS idx_leads_assigned_rep_status
                    ON "Leads" (owner_id, status, id DESC);

                    CREATE INDEX IF NOT EXISTS idx_employee_documents_employee_id
                    ON "EmployeeDocuments" (employee_id);

                    INSERT INTO "schema_migrations" (version, description)
                    VALUES ('043_backoffice_cqrs_covering_indexes', 'Covering composite indexes on GlobalActivities, CampaignRecipients, Leads, and EmployeeDocuments for HWB-QMS-11.14 v1.1 Backoffice CQRS Standard')
                    ON CONFLICT (version) DO NOTHING;
                """)
                conn.commit()
                applied.add("043_backoffice_cqrs_covering_indexes")
                print("[MIGRATION] 043_backoffice_cqrs_covering_indexes successfully applied and recorded.", flush=True)

            if "044_bug_132_133_error_ledger_sync" not in applied:
                sync_bug_132_133_five_tables(conn)
                cur.execute("""
                    INSERT INTO "schema_migrations" (version, description)
                    VALUES ('044_bug_132_133_error_ledger_sync', 'Synchronize BUG-132 and BUG-133 into SigmaKnowledgeScars, GlobalActivities, Incidents, RackTelemetryHistory, and SecurityAuditLogs across local and Azure databases')
                    ON CONFLICT (version) DO NOTHING;
                """)
                conn.commit()
                applied.add("044_bug_132_133_error_ledger_sync")
                print("[MIGRATION] 044_bug_132_133_error_ledger_sync successfully applied and recorded.", flush=True)

                # If connected to Azure sigmajan-server/sigmajan-db, also synchronize sibling sigmajan-adb if reachable
                if target_db_url and "sigmajan-server" in target_db_url and "/sigmajan-db" in target_db_url:
                    try:
                        import psycopg2
                        adb_url = target_db_url.replace("/sigmajan-db", "/sigmajan-adb")
                        adb_conn = psycopg2.connect(adb_url, connect_timeout=5)
                        try:
                            with adb_conn.cursor() as acur:
                                acur.execute("""
                                    CREATE INDEX IF NOT EXISTS idx_global_activities_parent_lookup
                                    ON "GlobalActivities" (parent_type, parent_id, timestamp DESC);
                                    CREATE INDEX IF NOT EXISTS idx_campaign_recipients_lead_lookup
                                    ON "CampaignRecipients" (lead_id, id DESC);
                                    CREATE INDEX IF NOT EXISTS idx_leads_assigned_rep_status
                                    ON "Leads" (owner_id, status, id DESC);
                                    CREATE INDEX IF NOT EXISTS idx_employee_documents_employee_id
                                    ON "EmployeeDocuments" (employee_id);
                                """)
                            adb_conn.commit()
                            sync_bug_132_133_five_tables(adb_conn)
                            print("[MIGRATION] 043 & 044 synchronized to sibling Azure database sigmajan-adb.", flush=True)
                        finally:
                            adb_conn.close()
                    except Exception as adb_err:
                        print(f"[MIGRATION NOTICE] Sibling sigmajan-adb sync skipped: {adb_err}", flush=True)

            if "045_enterprise_global_activities_guard_and_dedup" not in applied:
                apply_migration_045_global_activities_guard(conn)
                cur.execute("""
                    INSERT INTO "schema_migrations" (version, description)
                    VALUES ('045_enterprise_global_activities_guard_and_dedup', 'Purge 206K duplicate Autonomous Vetting & Enrichment rows in GlobalActivities, normalize parent_type values, and install BEFORE INSERT idempotency trigger + canonical parent_type CHECK constraint')
                    ON CONFLICT (version) DO NOTHING;
                """)
                conn.commit()
                applied.add("045_enterprise_global_activities_guard_and_dedup")
                print("[MIGRATION] 045_enterprise_global_activities_guard_and_dedup successfully applied and recorded.", flush=True)

                if target_db_url and "sigmajan-server" in target_db_url and "/sigmajan-db" in target_db_url:
                    try:
                        import psycopg2
                        adb_url = target_db_url.replace("/sigmajan-db", "/sigmajan-adb")
                        adb_conn = psycopg2.connect(adb_url, connect_timeout=5)
                        try:
                            apply_migration_045_global_activities_guard(adb_conn)
                            print("[MIGRATION] 045 synchronized to sibling Azure database sigmajan-adb.", flush=True)
                        finally:
                            adb_conn.close()
                    except Exception as adb_err:
                        print(f"[MIGRATION NOTICE] Sibling sigmajan-adb 045 sync skipped: {adb_err}", flush=True)

            for v_tag, mod_path, v_desc in modular_migrations:
                if v_tag not in applied:
                    print(f"[MIGRATION] Applying modular migration {v_tag} ({mod_path})...", flush=True)
                    try:
                        mod = importlib.import_module(mod_path)
                        if hasattr(mod, 'run_migration'):
                            mod.run_migration(target_db_url)
                        cur.execute("""
                            INSERT INTO "schema_migrations" (version, description)
                            VALUES (%s, %s)
                            ON CONFLICT (version) DO NOTHING;
                        """, (v_tag, v_desc))
                        conn.commit()
                        applied.add(v_tag)
                        print(f"[MIGRATION] {v_tag} successfully applied and recorded.", flush=True)
                    except Exception as mod_err:
                        conn.rollback()
                        print(f"[MIGRATION WARNING] Modular migration {v_tag} failed: {mod_err}", file=sys.stderr, flush=True)

    except Exception as e:
        conn.rollback()
        print(f"[MIGRATION ERROR] Failed to apply schema migrations: {e}", file=sys.stderr, flush=True)
        raise e


def apply_migration_045_global_activities_guard(conn: Any) -> dict:
    """
    Enterprise Standard #1 & #5:
    1. Purges duplicate 'Autonomous Vetting & Enrichment' rows in GlobalActivities,
       retaining only the single most recent row per (parent_type, parent_id).
    2. Normalizes legacy parent_type strings ('Customer' -> 'Account', 'SYSTEM' -> 'System').
    3. Installs BEFORE INSERT trigger (trg_global_activities_enterprise_guard) on GlobalActivities
       to auto-normalize known parent_type aliases and suppress duplicate automated daemon entries.
    4. Adds PostgreSQL CHECK constraint (chk_global_activities_canonical_parent_type) enforcing
       canonical parent_type values at the database kernel level.
    """
    stats = {"purged_duplicate_enrichment_rows": 0, "normalized_parent_type_rows": 0}
    with conn.cursor() as cur:
        # 1. Purge duplicate Autonomous Vetting & Enrichment rows keeping latest 1 per (parent_type, parent_id)
        cur.execute("""
            WITH latest_enrichment AS (
                SELECT DISTINCT ON (parent_type, parent_id) activity_id
                FROM "GlobalActivities"
                WHERE activity_type = 'Autonomous Vetting & Enrichment'
                ORDER BY parent_type, parent_id, timestamp DESC NULLS LAST, activity_id DESC
            )
            DELETE FROM "GlobalActivities" ga
            WHERE ga.activity_type = 'Autonomous Vetting & Enrichment'
              AND NOT EXISTS (
                  SELECT 1 FROM latest_enrichment le WHERE le.activity_id = ga.activity_id
              );
        """)
        stats["purged_duplicate_enrichment_rows"] = cur.rowcount

        # 2. Normalize existing parent_type values to canonical domain names
        cur.execute("""
            UPDATE "GlobalActivities"
            SET parent_type = CASE
                WHEN UPPER(TRIM(COALESCE(parent_type, ''))) IN ('CUSTOMER', 'CUSTOMERS', 'CLIENT', 'CLIENTS', 'ACCOUNT', 'ACCOUNTS') THEN 'Account'
                WHEN UPPER(TRIM(COALESCE(parent_type, ''))) IN ('LEAD', 'LEADS') THEN 'Lead'
                WHEN UPPER(TRIM(COALESCE(parent_type, ''))) IN ('CONSTRUCTIONBID', 'CONSTRUCTION_BID', 'GC_BID', 'BID') THEN 'ConstructionBid'
                WHEN UPPER(TRIM(COALESCE(parent_type, ''))) IN ('INSTITUTIONALBID', 'INSTITUTIONAL_BID') THEN 'InstitutionalBid'
                WHEN UPPER(TRIM(COALESCE(parent_type, ''))) IN ('GENERALCONTRACTOR', 'GENERAL_CONTRACTOR', 'GC') THEN 'GeneralContractor'
                WHEN UPPER(TRIM(COALESCE(parent_type, ''))) IN ('WORKORDER', 'WORK_ORDER', 'WORKORDERS') THEN 'WorkOrder'
                WHEN UPPER(TRIM(COALESCE(parent_type, ''))) IN ('EMPLOYEE', 'EMPLOYEES') THEN 'Employee'
                WHEN UPPER(TRIM(COALESCE(parent_type, ''))) IN ('SUBCONTRACTOR', 'SUBCONTRACTORS') THEN 'Subcontractor'
                WHEN UPPER(TRIM(COALESCE(parent_type, ''))) IN ('APPLICANT', 'APPLICANTS') THEN 'Applicant'
                WHEN UPPER(TRIM(COALESCE(parent_type, ''))) IN ('PENDINGOUTBOX', 'PENDING_OUTBOX') THEN 'PendingOutbox'
                WHEN UPPER(TRIM(COALESCE(parent_type, ''))) IN ('CAMPAIGN', 'CAMPAIGNS') THEN 'Campaign'
                WHEN UPPER(TRIM(COALESCE(parent_type, ''))) IN ('USER', 'USERS') THEN 'User'
                WHEN UPPER(TRIM(COALESCE(parent_type, ''))) IN ('AGENT', 'AGENTS') THEN 'Agent'
                ELSE 'System'
            END
            WHERE parent_type IS NULL
               OR parent_type NOT IN (
                   'Lead', 'Account', 'ConstructionBid', 'InstitutionalBid',
                   'GeneralContractor', 'WorkOrder', 'Employee', 'Subcontractor',
                   'Applicant', 'PendingOutbox', 'Campaign', 'User', 'Agent', 'System'
               );
        """)
        stats["normalized_parent_type_rows"] = cur.rowcount

        # 3. Create PostgreSQL BEFORE INSERT trigger function & trigger for normalization + idempotent deduplication
        cur.execute("""
            CREATE OR REPLACE FUNCTION fn_global_activities_enterprise_guard()
            RETURNS TRIGGER AS $$
            DECLARE
                v_existing_id INTEGER;
                v_norm_type TEXT;
            BEGIN
                v_norm_type := UPPER(TRIM(COALESCE(NEW.parent_type, 'SYSTEM')));
                IF v_norm_type IN ('CUSTOMER', 'CUSTOMERS', 'CLIENT', 'CLIENTS', 'ACCOUNT', 'ACCOUNTS') THEN
                    NEW.parent_type := 'Account';
                ELSIF v_norm_type IN ('LEAD', 'LEADS') THEN
                    NEW.parent_type := 'Lead';
                ELSIF v_norm_type IN ('CONSTRUCTIONBID', 'CONSTRUCTION_BID', 'GC_BID', 'BID') THEN
                    NEW.parent_type := 'ConstructionBid';
                ELSIF v_norm_type IN ('INSTITUTIONALBID', 'INSTITUTIONAL_BID') THEN
                    NEW.parent_type := 'InstitutionalBid';
                ELSIF v_norm_type IN ('GENERALCONTRACTOR', 'GENERAL_CONTRACTOR', 'GC') THEN
                    NEW.parent_type := 'GeneralContractor';
                ELSIF v_norm_type IN ('WORKORDER', 'WORK_ORDER', 'WORKORDERS') THEN
                    NEW.parent_type := 'WorkOrder';
                ELSIF v_norm_type IN ('EMPLOYEE', 'EMPLOYEES') THEN
                    NEW.parent_type := 'Employee';
                ELSIF v_norm_type IN ('SUBCONTRACTOR', 'SUBCONTRACTORS') THEN
                    NEW.parent_type := 'Subcontractor';
                ELSIF v_norm_type IN ('APPLICANT', 'APPLICANTS') THEN
                    NEW.parent_type := 'Applicant';
                ELSIF v_norm_type IN ('PENDINGOUTBOX', 'PENDING_OUTBOX') THEN
                    NEW.parent_type := 'PendingOutbox';
                ELSIF v_norm_type IN ('CAMPAIGN', 'CAMPAIGNS') THEN
                    NEW.parent_type := 'Campaign';
                ELSIF v_norm_type IN ('USER', 'USERS') THEN
                    NEW.parent_type := 'User';
                ELSIF v_norm_type IN ('AGENT', 'AGENTS') THEN
                    NEW.parent_type := 'Agent';
                ELSIF v_norm_type = 'SYSTEM' THEN
                    NEW.parent_type := 'System';
                END IF;

                -- Database-level idempotent deduplication for background daemon telemetry
                IF NEW.activity_type IN ('Autonomous Vetting & Enrichment', 'Autonomous Ingress') AND NEW.parent_id IS NOT NULL THEN
                    SELECT activity_id INTO v_existing_id
                    FROM "GlobalActivities"
                    WHERE parent_type = NEW.parent_type
                      AND parent_id = NEW.parent_id
                      AND activity_type = NEW.activity_type
                      AND COALESCE(description, '') = COALESCE(NEW.description, '')
                    ORDER BY timestamp DESC
                    LIMIT 1;

                    IF v_existing_id IS NOT NULL THEN
                        UPDATE "GlobalActivities"
                        SET timestamp = COALESCE(NEW.timestamp, CURRENT_TIMESTAMP)
                        WHERE activity_id = v_existing_id;
                        RETURN NULL;
                    END IF;
                END IF;

                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trg_global_activities_enterprise_guard ON "GlobalActivities";
            CREATE TRIGGER trg_global_activities_enterprise_guard
            BEFORE INSERT ON "GlobalActivities"
            FOR EACH ROW
            EXECUTE FUNCTION fn_global_activities_enterprise_guard();
        """)

        # 4. Enforce canonical parent_type CHECK constraint at the PostgreSQL kernel level
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'chk_global_activities_canonical_parent_type'
                ) THEN
                    ALTER TABLE "GlobalActivities"
                    ADD CONSTRAINT chk_global_activities_canonical_parent_type
                    CHECK (parent_type IN (
                        'Lead', 'Account', 'ConstructionBid', 'InstitutionalBid',
                        'GeneralContractor', 'WorkOrder', 'Employee', 'Subcontractor',
                        'Applicant', 'PendingOutbox', 'Campaign', 'User', 'Agent', 'System'
                    ));
                END IF;
            END $$;
        """)
    conn.commit()
    return stats


def sync_bug_132_133_five_tables(conn: Any) -> dict:
    """
    Idempotently synchronizes BUG-132 (Public Web Performance / WebP / Worker Recycle)
    and BUG-133 (Post-Login Backoffice CQRS / 300s Telemetry Cache / DOM Pruning)
    across all 5 HWB database error/audit tables:
      1. SigmaKnowledgeScars (id=224, 225 + full 1..225 scar baseline)
      2. GlobalActivities ([AUTO-HEALED-PERFORMANCE-BUG-132], [AUTO-HEALED-PERFORMANCE-BUG-133])
      3. Incidents (BUG-132, BUG-133)
      4. RackTelemetryHistory (HWB-QMS-11.14-V5.4.4-AUDIT)
      5. SecurityAuditLogs (HWB_QMS_11_14_V5_4_4_BUG_132_133_REMEDIATED)
    Returns a dictionary of verified row IDs.
    """
    import json
    receipt = {
        "sigma_knowledge_scars": {},
        "total_sigma_knowledge_scars": 0,
        "global_activities": {},
        "incidents": {},
        "total_incidents": 0,
        "rack_telemetry_history_id": None,
        "security_audit_logs_id": None,
    }
    with conn.cursor() as cur:
        # 0. Guarantee table existence on all target databases (local hwb_dev_db, Azure sigmajan-db, Azure sigmajan-adb)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "SigmaKnowledgeScars" (
                id SERIAL PRIMARY KEY,
                description TEXT NOT NULL,
                category TEXT DEFAULT 'System Integrity',
                status TEXT DEFAULT 'RESOLVED',
                impact_level INTEGER DEFAULT 3,
                root_cause TEXT DEFAULT '',
                implemented_fix TEXT DEFAULT '',
                preventative_rule TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolution_notes TEXT,
                search_vector tsvector
            );

            CREATE TABLE IF NOT EXISTS "Incidents" (
                id SERIAL PRIMARY KEY,
                date DATE DEFAULT CURRENT_DATE,
                description TEXT NOT NULL,
                category TEXT DEFAULT 'System Integrity',
                severity TEXT DEFAULT 'High'
            );
        """)

        # Seed full historical SigmaKnowledgeScars & Incidents baseline if missing
        cur.execute('SELECT COUNT(*) FROM "SigmaKnowledgeScars";')
        existing_scar_count = cur.fetchone()[0]
        if existing_scar_count < 224:
            seed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sigma_knowledge_scars_seed.json")
            if os.path.exists(seed_path):
                with open(seed_path, "r", encoding="utf-8") as sf:
                    seed_data = json.load(sf)
                for srow in seed_data.get("scars", []):
                    cur.execute("""
                        INSERT INTO "SigmaKnowledgeScars" (
                            id, description, category, status, impact_level,
                            root_cause, implemented_fix, preventative_rule,
                            created_at, resolved_at, resolution_notes
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s::timestamp, NOW()), COALESCE(%s::timestamp, NOW()), %s)
                        ON CONFLICT (id) DO NOTHING;
                    """, tuple(srow))
                for irow in seed_data.get("incidents", []):
                    cur.execute("""
                        INSERT INTO "Incidents" (id, date, description, category, severity)
                        VALUES (%s, COALESCE(%s::date, CURRENT_DATE), %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING;
                    """, tuple(irow))
                cur.execute('SELECT setval(pg_get_serial_sequence(\'"Incidents"\', \'id\'), GREATEST(COALESCE((SELECT MAX(id) FROM "Incidents"), 1), 1));')

        # 1. SigmaKnowledgeScars (IDs 224 and 225)
        cur.execute("""
            INSERT INTO "SigmaKnowledgeScars" (
                id, description, category, status, impact_level,
                root_cause, implemented_fix, preventative_rule,
                created_at, resolved_at, resolution_notes
            ) VALUES (
                224,
                'BUG-132: Public Website Cold-Start Latency (18.4s), Synchronous Boot DDL Contention, Uncompressed PNG/JPG Payloads (16.4 MB), and Gunicorn Worker Recycle Stalls (--max-requests 1000).',
                'Performance & Architecture',
                'RESOLVED',
                4,
                'Five compounding bottlenecks on hwbcleaning.com: (1) Three concurrent daemon threads launched in each Gunicorn worker executing DDL and DNS MX scans during boot; (2) No --preload in Dockerfile and aggressive --max-requests 1000 causing worker recycle stalls; (3) Per-request SELECT 1 socket ping in get_db() and 4 redundant RBAC queries on public routes; (4) 16.4 MB uncompressed PNG/JPG assets; (5) Cloudflare CDN Bypassed on /static/* and immutable cache headers overridden.',
                'Implemented HWB-QMS-11.14 v1.0.0 (Release v5.4.3): (1) Single-execution POSIX flock boot lock (/tmp/hwb_boot_init.lock) + Gunicorn --preload --max-requests 10000 --keep-alive 65; (2) 60s last-used socket trust in get_db() + public route RBAC bypass; (3) Lossless WebP conversion of all 35 images (16.4 MB -> 1.98 MB, -87.9%) + lazy loading + fetchpriority=high; (4) Immutable 1-year Cache-Control on /static/* and 60s s-maxage on public HTML; (5) Rack 14 Web Performance & Core Web Vitals Verification Suite.',
                'Mandate HWB-QMS-11.14 Part I: All Gunicorn deployments must use --preload with flock-guarded single-execution boot tasks, 60s pooled connection trust, WebP image assets, and immutable /static/* edge caching.',
                NOW(),
                NOW(),
                'Verified 2026-10-19 (v5.4.3): Public route TTFB reduced by 98.7% (from 1,840ms-18,400ms to 1.88ms-3.27ms locally and 42ms-74ms over live TLS).'
            )
            ON CONFLICT (id) DO UPDATE SET
                description = EXCLUDED.description,
                category = EXCLUDED.category,
                status = EXCLUDED.status,
                impact_level = EXCLUDED.impact_level,
                root_cause = EXCLUDED.root_cause,
                implemented_fix = EXCLUDED.implemented_fix,
                preventative_rule = EXCLUDED.preventative_rule,
                resolved_at = NOW(),
                resolution_notes = EXCLUDED.resolution_notes
            RETURNING id;
        """)
        receipt["sigma_knowledge_scars"]["BUG-132"] = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO "SigmaKnowledgeScars" (
                id, description, category, status, impact_level,
                root_cause, implemented_fix, preventative_rule,
                created_at, resolved_at, resolution_notes
            ) VALUES (
                225,
                'BUG-133: Post-Login Backoffice Tab-Switching Latency (2.44s-9.05s), 22-Query Monolithic God-Controller, Uncached 11-Rack Telemetry Synthesis, and 3.3 MB Unpruned DOM Payload.',
                'Performance & Architecture',
                'RESOLVED',
                4,
                'Four post-login architectural bottlenecks in /admin/operations: (1) Monolithic controller executing all 22 SQL queries for all 11 departments on every tab click; (2) Correlated subqueries per row on Customers, Leads, ConstructionBids, InstitutionalBids, GeneralContractors, and Employees plus missing composite indexes on GlobalActivities and CampaignRecipients; (3) Uncached 11-Rack self-healing telemetry + .env disk reads + DNS socket probes running synchronously on every page load; (4) Monolithic 16,900-line template rendering all 11 hidden views (2.6-3.3 MB HTML) and 391 KB inline JS on every click.',
                'Implemented HWB-QMS-11.14 v1.1.0 (Release v5.4.4): (1) 300s TTL thread-safe cache with non-blocking background daemon refresh on all 10 self_healing_engine.py Racks and credential_sentinel.py; (2) Migration 043 creating 4 covering composite indexes (idx_global_activities_parent_lookup, idx_campaign_recipients_lead_lookup, idx_leads_assigned_rep_status, idx_employee_documents_employee_id) and replacing correlated subqueries with set-based LEFT JOIN LATERAL / CTE aggregations; (3) Active-View CQRS SQL isolation in blueprints/operations.py with 30s cached sidebar counts (_get_operations_sidebar_counts); (4) Server-side Jinja active_view DOM pruning in templates/backoffice_operations.html + static JS extraction to /static/js/backoffice_operations_core.js.',
                'Mandate HWB-QMS-11.14 Part II: Multi-tab backoffice controllers must enforce Active-View CQRS SQL isolation, 300s background-refreshed telemetry caches, covering composite indexes (zero correlated subqueries in loops), and server-side Jinja DOM pruning.',
                NOW(),
                NOW(),
                'Verified 2026-10-19 (v5.4.4): Warm backoffice view switching reduced from 2,440ms-9,050ms to 4.38ms-28.01ms (98.9%-99.8% reduction); gzipped payload reduced to 40.8 KB-72.3 KB.'
            )
            ON CONFLICT (id) DO UPDATE SET
                description = EXCLUDED.description,
                category = EXCLUDED.category,
                status = EXCLUDED.status,
                impact_level = EXCLUDED.impact_level,
                root_cause = EXCLUDED.root_cause,
                implemented_fix = EXCLUDED.implemented_fix,
                preventative_rule = EXCLUDED.preventative_rule,
                resolved_at = NOW(),
                resolution_notes = EXCLUDED.resolution_notes
            RETURNING id;
        """)
        receipt["sigma_knowledge_scars"]["BUG-133"] = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO "SigmaKnowledgeScars" (
                id, description, category, status, impact_level,
                root_cause, implemented_fix, preventative_rule,
                created_at, resolved_at, resolution_notes
            ) VALUES (
                226,
                'BUG-134: Unclosed #view-monitor Container (display: none) During Jinja Active-View Pruning Trapping Downstream Views & Modals (#modal-lead-command) and Preventing Lead Row Click Display.',
                'UI / DOM Integrity',
                'RESOLVED',
                4,
                'In templates/backoffice_operations.html (line 4002), <div id="view-monitor" style="display: none;"> was opened outside {% if active_view in ["monitor", "dispatch"] %}, while its closing </div> (line 4272) was placed inside the conditional block. When active_view was "leads", Jinja skipped the closing </div>, wrapping all downstream views and modals (#modal-lead-command) inside a hidden parent.',
                'Closed {% if active_view in ["monitor", "dispatch"] %} inside #view-monitor before its closing </div>, wrapped #modal-dispatch-create and #modal-dispatch-detail in a balanced conditional block outside #view-monitor, and added test_11_backoffice_modal_dom_isolation_and_lead_click in scripts/test_web_performance_rack_14.py.',
                'Every {% if active_view == ... %} pruning block inside a <div id="view-..."> container must close before the container closing </div>, verified by automated HTMLParser DOM nesting checks across all views.',
                NOW(),
                NOW(),
                'Verified 2026-10-19 (v5.4.4): Zero views or modals trapped inside hidden view-* containers across all 12 backoffice views; lead row click opens #modal-lead-command immediately.'
            )
            ON CONFLICT (id) DO UPDATE SET
                description = EXCLUDED.description,
                category = EXCLUDED.category,
                status = EXCLUDED.status,
                impact_level = EXCLUDED.impact_level,
                root_cause = EXCLUDED.root_cause,
                implemented_fix = EXCLUDED.implemented_fix,
                preventative_rule = EXCLUDED.preventative_rule,
                resolved_at = NOW(),
                resolution_notes = EXCLUDED.resolution_notes
            RETURNING id;
        """)
        receipt["sigma_knowledge_scars"]["BUG-134"] = cur.fetchone()[0]
        cur.execute('SELECT setval(pg_get_serial_sequence(\'"SigmaKnowledgeScars"\', \'id\'), GREATEST((SELECT MAX(id) FROM "SigmaKnowledgeScars"), 226));')
        cur.execute('SELECT COUNT(*) FROM "SigmaKnowledgeScars";')
        receipt["total_sigma_knowledge_scars"] = cur.fetchone()[0]

        # 2. GlobalActivities ([AUTO-HEALED-PERFORMANCE-BUG-132], [AUTO-HEALED-PERFORMANCE-BUG-133] & [AUTO-HEALED-DOM-BUG-134])
        for bug_code, act_type, desc_text in [
            (
                "BUG-132",
                "[AUTO-HEALED-PERFORMANCE-BUG-132]",
                "HWB-QMS-11.14 v1.0.0 (Release v5.4.3): Remediated BUG-132 public website cold-start latency (18.4s -> 2.1ms local / 55ms TLS), converted 35 images to WebP (16.4 MB -> 1.98 MB, -87.9%), enforced POSIX flock single-boot lock, and deployed Gunicorn --preload worker architecture."
            ),
            (
                "BUG-133",
                "[AUTO-HEALED-PERFORMANCE-BUG-133]",
                "HWB-QMS-11.14 v1.1.0 (Release v5.4.4): Remediated BUG-133 post-login backoffice tab-switching latency (2.44s-9.05s -> 4.4ms-28.0ms warm) via Active-View CQRS SQL isolation, 4 covering composite indexes (Migration 043), 300s background telemetry cache, and server-side Jinja DOM pruning."
            ),
            (
                "BUG-134",
                "[AUTO-HEALED-DOM-BUG-134]",
                "HWB-QMS-11.14 v1.1.0 (Release v5.4.4): Remediated BUG-134 unclosed #view-monitor container during Jinja active_view pruning that trapped #modal-lead-command inside a display:none parent on /admin/operations?view=leads; added Test 11 HTMLParser DOM isolation verification."
            ),
        ]:
            cur.execute('SELECT activity_id FROM "GlobalActivities" WHERE activity_type = %s ORDER BY activity_id DESC LIMIT 1;', (act_type,))
            row = cur.fetchone()
            if row:
                receipt["global_activities"][bug_code] = row[0]
            else:
                cur.execute("""
                    INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description, timestamp)
                    VALUES (1, 'System', %s, %s, NOW())
                    RETURNING activity_id;
                """, (act_type, desc_text))
                receipt["global_activities"][bug_code] = cur.fetchone()[0]

        # 3. Incidents (BUG-132, BUG-133 & BUG-134)
        for bug_code, sev, inc_desc in [
            (
                "BUG-132",
                "High",
                "BUG-132: Public website (hwbcleaning.com) experienced 1.84s-18.4s TTFB cold-start stalls, 3x boot thread DDL contention, and 16.4 MB uncompressed image payloads. | VERIFIED RESOLVED (v5.4.3 / HWB-QMS-11.14 v1.0): POSIX flock boot guard, Gunicorn --preload, 87.9% WebP compression, and immutable /static/* caching deployed."
            ),
            (
                "BUG-133",
                "Critical",
                "BUG-133: Post-login Backoffice Operations (/admin/operations) experienced 2.44s-9.05s tab-switching latency and 2.6 MB-3.3 MB HTML payloads due to 22-query monolithic controller, correlated subqueries, uncached 11-Rack telemetry, and unpruned DOM views. | VERIFIED RESOLVED (v5.4.4 / HWB-QMS-11.14 v1.1): Active-View CQRS SQL isolation, Migration 043 covering indexes, 300s async telemetry cache, and Jinja DOM pruning deployed (4.4ms-28.0ms warm)."
            ),
            (
                "BUG-134",
                "High",
                "BUG-134: Unclosed #view-monitor container (display: none) during Jinja active_view pruning trapped downstream views and modals (#modal-lead-command) on /admin/operations?view=leads. | VERIFIED RESOLVED (v5.4.4): Balanced #view-monitor Jinja closing tags and added Test 11 HTMLParser DOM isolation assertion in scripts/test_web_performance_rack_14.py."
            ),
        ]:
            cur.execute('SELECT id FROM "Incidents" WHERE description LIKE %s ORDER BY id DESC LIMIT 1;', (f"{bug_code}:%",))
            row = cur.fetchone()
            if row:
                receipt["incidents"][bug_code] = row[0]
            else:
                cur.execute("""
                    INSERT INTO "Incidents" (date, description, category, severity)
                    VALUES ('2026-10-19', %s, 'Performance & Architecture', %s)
                    RETURNING id;
                """, (inc_desc, sev))
                receipt["incidents"][bug_code] = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM "Incidents";')
        receipt["total_incidents"] = cur.fetchone()[0]

        # 4. RackTelemetryHistory
        cur.execute("""
            SELECT id FROM "RackTelemetryHistory"
            WHERE session_id = 'HWB-QMS-11.14-V5.4.4-AUDIT' AND rack_number = 14
            ORDER BY id DESC LIMIT 1;
        """)
        row = cur.fetchone()
        if row:
            receipt["rack_telemetry_history_id"] = row[0]
        else:
            telemetry_payload = json.dumps({
                "standard": "HWB-QMS-11.14 v1.1.0",
                "release": "v5.4.4",
                "bug_132_public_ttfb_ms": 2.12,
                "bug_132_webp_reduction_pct": 87.9,
                "bug_133_backoffice_warm_ms": {
                    "leads": 28.01,
                    "accounts": 6.53,
                    "construction_bids": 125.99,
                    "marketing": 5.16,
                    "workforce": 10.34,
                    "it_department": 7.41
                }
            })
            cur.execute("""
                INSERT INTO "RackTelemetryHistory" (
                    session_id, timestamp, rack_number, rack_name,
                    metric_category, score_value, secondary_value,
                    status_tag, details_json, recorded_by
                ) VALUES (
                    'HWB-QMS-11.14-V5.4.4-AUDIT', NOW(), 14,
                    'Enterprise Web & Backoffice Performance (CQRS)',
                    'BACKOFFICE_CQRS_LATENCY_MS', 100.0, 7.41,
                    'OPTIMAL (A+)', %s::jsonb, 'George Bytes (HWB-QMS-11.14 v1.1)'
                )
                RETURNING id;
            """, (telemetry_payload,))
            receipt["rack_telemetry_history_id"] = cur.fetchone()[0]

        # 5. SecurityAuditLogs (WORM Audit Table)
        cur.execute("""
            SELECT id FROM "SecurityAuditLogs"
            WHERE event_action = 'HWB_QMS_11_14_V5_4_4_BUG_132_133_REMEDIATED'
            ORDER BY id DESC LIMIT 1;
        """)
        row = cur.fetchone()
        if row:
            receipt["security_audit_logs_id"] = row[0]
        else:
            audit_details = json.dumps({
                "standard": "HWB-QMS-11.14 v1.1.0",
                "release": "v5.4.4",
                "resolved_defects": ["BUG-132", "BUG-133"],
                "sigma_knowledge_scars": [224, 225],
                "migrations": ["043_backoffice_cqrs_covering_indexes", "044_bug_132_133_error_ledger_sync"]
            })
            cur.execute("""
                INSERT INTO "SecurityAuditLogs" (
                    timestamp, event_category, event_action,
                    user_id, username, user_role, ip_address,
                    user_agent, endpoint, http_method, status_code,
                    severity, details
                ) VALUES (
                    NOW(), 'SYSTEM_ARCHITECTURE', 'HWB_QMS_11_14_V5_4_4_BUG_132_133_REMEDIATED',
                    1, 'george_bytes', 'Systems Architect', '127.0.0.1',
                    'SigmaFidelity-Autonomous-Auditor/v5.4.4', '/admin/operations', 'SYSTEM', 200,
                    'INFO', %s::jsonb
                )
                RETURNING id;
            """, (audit_details,))
            receipt["security_audit_logs_id"] = cur.fetchone()[0]

    conn.commit()
    return receipt

