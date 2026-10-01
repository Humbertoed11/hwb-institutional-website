"""
SigmaFidelity™ Institutional Partner Automated Onboarding Engine (Model C)
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Authority: Humberto Dominguez (CEO)
Architect: George (Systems Architect & mbB)
"""

import os
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")


def get_connection(db_url: str):
    """Establishes a PostgreSQL database connection."""
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def onboard_partner(
    company_name: str = "Bosanna LLC",
    slug: str = "bosanna",
    contact_name: str = "Angelica Hudgins",
    contact_email: str = "ahudgins@bosanna.com",
    contact_phone: str = "(214) 862-2300",
    company_address: str = "4514 Travis St, Suite 200",
    city: str = "Dallas",
    state: str = "TX",
    zip_code: str = "75205",
    contract_number: str = "TIPS #260102",
    facility_name: str = "Collin College Frisco Campus",
    facility_address: str = "9700 Wade Blvd, Frisco, TX 75035",
    sqf: int = 125000,
    brand_color: str = "#063333",
    brand_logo_url: str = "https://bosanna.com/wp-content/uploads/2023/10/bosanna-logo.png",
    db_url: str = DB_URL
) -> Dict[str, Any]:
    """
    Executes end-to-end automated onboarding for an institutional prime contractor.
    Provisions Customers master entry, AcademyTenants LMS workspace, WorkOrders schedule,
    and stages the official executive welcome letter in PendingOutbox.
    """
    print(f"\n=======================================================")
    print(f"  SigmaFidelity™ Automated Partner Onboarding: {company_name}")
    print(f"=======================================================")

    conn = get_connection(db_url)
    result = {
        "status": "success",
        "company_name": company_name,
        "slug": slug,
        "customer_id": None,
        "tenant_id": None,
        "work_order_id": None,
        "outbox_id": None,
        "user_id": None
    }

    try:
        with conn.cursor() as cur:
            # 1. Provision / Update Master Customer Record
            print(f"[1/6] Provisioning master customer record in 'Customers'...")
            cur.execute("""
                SELECT customer_id FROM "Customers" 
                WHERE LOWER(company_name) = LOWER(%s) OR email = %s;
            """, (company_name, contact_email))
            cust = cur.fetchone()

            if cust:
                customer_id = cust["customer_id"]
                cur.execute("""
                    UPDATE "Customers" SET
                        contact_person_name = %s,
                        company_address = %s,
                        city = %s,
                        state = %s,
                        zip = %s,
                        phone = %s,
                        email = %s,
                        quote_number = %s,
                        contract_period = %s,
                        frequency = 'Daily (Evening Janitorial + Day Porter)',
                        payment_terms = 'Net 30',
                        website = 'https://bosanna.com/',
                        status = 'Active',
                        sqf = %s,
                        cleaning_delivery_model = 'Model C (White-Label Prime Partner)',
                        notes = %s
                    WHERE customer_id = %s;
                """, (
                    contact_name,
                    company_address,
                    city,
                    state,
                    zip_code,
                    contact_phone,
                    contact_email,
                    f"{slug.upper()}-TIPS-{datetime.now().year}",
                    f"{contract_number} / {facility_name}",
                    sqf,
                    f"Prime contractor under {contract_number} servicing {facility_name}.",
                    customer_id
                ))
                print(f"  ✓ Updated existing customer ID: {customer_id}")
            else:
                cur.execute("""
                    INSERT INTO "Customers" (
                        company_name, contact_person_name, company_address, city, state, zip,
                        phone, email, quote_number, contract_period, frequency, payment_terms,
                        website, status, sqf, cleaning_delivery_model, notes, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, 'Active', %s, 'Model C (White-Label Prime Partner)', %s, CURRENT_DATE
                    ) RETURNING customer_id;
                """, (
                    company_name,
                    contact_name,
                    company_address,
                    city,
                    state,
                    zip_code,
                    contact_phone,
                    contact_email,
                    f"{slug.upper()}-TIPS-{datetime.now().year}",
                    f"{contract_number} / {facility_name}",
                    "Daily (Evening Janitorial + Day Porter)",
                    "Net 30",
                    "https://bosanna.com/",
                    sqf,
                    f"Prime contractor under {contract_number} servicing {facility_name}."
                ))
                customer_id = cur.fetchone()["customer_id"]
                print(f"  ✓ Inserted new customer ID: {customer_id}")
            result["customer_id"] = customer_id

            # 2. Provision / Update Academy Tenant Workspace
            print(f"[2/6] Provisioning Academy LMS workspace in 'AcademyTenants'...")
            cur.execute("""
                SELECT id FROM "AcademyTenants" WHERE slug = %s;
            """, (slug,))
            tenant = cur.fetchone()

            if tenant:
                tenant_id = tenant["id"]
                cur.execute("""
                    UPDATE "AcademyTenants" SET
                        display_name = %s,
                        brand_logo_url = %s,
                        brand_primary_color = %s,
                        tenant_type = 'PRIME_PARTNER',
                        subscription_tier = 'MODEL_C_ENTERPRISE',
                        contact_email = %s,
                        is_active = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                """, (
                    f"{company_name} Facilities Management",
                    brand_logo_url,
                    brand_color,
                    contact_email,
                    tenant_id
                ))
                print(f"  ✓ Updated existing AcademyTenant ID: {tenant_id}")
            else:
                cur.execute("""
                    INSERT INTO "AcademyTenants" (
                        slug, display_name, brand_logo_url, brand_primary_color,
                        tenant_type, subscription_tier, contact_email, is_active
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                    RETURNING id;
                """, (
                    slug,
                    f"{company_name} Facilities Management",
                    brand_logo_url,
                    brand_color,
                    "PRIME_PARTNER",
                    "MODEL_C_ENTERPRISE",
                    contact_email
                ))
                tenant_id = cur.fetchone()["id"]
                print(f"  ✓ Inserted new AcademyTenant ID: {tenant_id}")
            result["tenant_id"] = tenant_id

            # 3. Provision Partner Executive User Access
            print(f"[3/6] Verifying executive credentials in 'Users'...")
            username = contact_name.lower().replace(" ", "")[:8]
            cur.execute("""
                SELECT id, username, role FROM "Users" 
                WHERE LOWER(username) = %s OR LOWER(email) = LOWER(%s);
            """, (username, contact_email))
            user = cur.fetchone()

            if user:
                user_id = user["id"]
                cur.execute("""
                    UPDATE "Users" SET
                        role = %s,
                        full_name = %s,
                        email = %s,
                        status = 'Active'
                    WHERE id = %s;
                """, (f"Partner_{slug.capitalize()}", contact_name, contact_email, user_id))
                print(f"  ✓ Updated user '{user['username']}' (ID: {user_id}) with role: Partner_{slug.capitalize()}")
            else:
                # Default pbkdf2 hash for initial onboarding password (bosanna2026!)
                pw_hash = "scrypt:32768:8:1$xHk...default"
                cur.execute("""
                    INSERT INTO "Users" (
                        username, email, password_hash, role, full_name, status, created_at
                    ) VALUES (%s, %s, %s, %s, %s, 'Active', CURRENT_TIMESTAMP)
                    RETURNING id;
                """, (
                    username,
                    contact_email,
                    "scrypt:32768:8:1$pG8c187K9v0L$c98fa3910cbe7d08",
                    f"Partner_{slug.capitalize()}",
                    contact_name
                ))
                user_id = cur.fetchone()["id"]
                print(f"  ✓ Provisioned user '{username}' (ID: {user_id})")
            result["user_id"] = user_id

            # Link Academy Tenant Access to Master Safety Course
            cur.execute("""
                SELECT id FROM "AcademyTenantAccess" 
                WHERE tenant_id = %s AND course_id = 1;
            """, (tenant_id,))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO "AcademyTenantAccess" (tenant_id, course_id, seat_limit, is_active)
                    VALUES (%s, 1, 50, TRUE);
                """, (tenant_id,))
                print(f"  ✓ Linked tenant {tenant_id} to Safety Course in AcademyTenantAccess")

            # 4. Provision Recurring Campus WorkOrder Schedule
            print(f"[4/6] Provisioning recurring campus schedule in 'WorkOrders'...")
            cur.execute("""
                SELECT work_order_id FROM "WorkOrders" 
                WHERE customer_id = %s AND status = 'Scheduled'
                ORDER BY scheduled_date DESC LIMIT 1;
            """, (customer_id,))
            wo = cur.fetchone()

            if wo:
                work_order_id = wo["work_order_id"]
                print(f"  ✓ Active WorkOrder already scheduled: #{work_order_id}")
            else:
                cur.execute("""
                    INSERT INTO "WorkOrders" (
                        customer_id, status, scheduled_date, scheduled_time,
                        client_notes, crew_notes, created_at
                    ) VALUES (
                        %s, 'Scheduled', CURRENT_DATE, '17:00',
                        %s, %s, CURRENT_DATE
                    ) RETURNING work_order_id;
                """, (
                    customer_id,
                    f"{contract_number} - Daily Evening Custodial Services at {facility_name}. Scope includes academic corridors, smart lecture halls, STEM laboratory sanitation, and 100% restroom terminal hygiene.",
                    f"Dock Ingress: Access loading bay via {facility_address}. Must wear Bosanna / TIPS photo ID badge at all times."
                ))
                work_order_id = cur.fetchone()["work_order_id"]
                print(f"  ✓ Created new recurring WorkOrder ID: #{work_order_id}")
            result["work_order_id"] = work_order_id

            # 5. Stage Official Executive Welcome Dispatch in PendingOutbox
            print(f"[5/6] Staging official executive welcome letter in 'PendingOutbox'...")
            cur.execute("""
                SELECT id FROM "PendingOutbox" 
                WHERE recipient = %s AND subject LIKE '%%Institutional Partner Activation%%';
            """, (contact_email,))
            existing_mail = cur.fetchone()

            if existing_mail:
                outbox_id = existing_mail["id"]
                print(f"  ✓ Welcome dispatch already staged (ID: #{outbox_id})")
            else:
                email_subject = f"Institutional Partner Activation | {company_name} ({contract_number}) & {facility_name}"
                email_body = f"""HWB CLEANING SERVICES LLC | INSTITUTIONAL PARTNERSHIP DIVISION
OFFICIAL LETTERHEAD: HWB-COM-001 (EXECUTIVE DISPATCH)
DATE: {datetime.now().strftime('%m/%d/%Y')}

TO: {contact_name}, Executive Director
ORGANIZATION: {company_name}
CONTRACT REFERENCE: {contract_number} (TIPS National Cooperative Award)
FACILITY DEPLOYMENT: {facility_name} ({facility_address})

Dear Ms. Hudgins,

We are pleased to confirm that the SigmaFidelity™ Model C operational infrastructure for {company_name} is officially active and ready for immediate deployment.

Your white-labeled digital ecosystem includes the following dedicated portals:

1. PRIME CONTRACTOR OPERATIONS PORTAL:
   Direct URL: http://mop.test:5000/portal/{slug}/portal
   Magic Access: http://mop.test:5000/portal/{slug}/magic-login
   Features: Real-time candidate roster, bench-ready standby counts, dock inspection status, and 1-click auditor compliance dossier exports.

2. BILINGUAL TECHNICIAN INTAKE PORTAL:
   Direct URL: http://mop.test:5000/onboard/{slug}
   Features: Automated Texas phone and ID verification, Texas Education Code § 22.0834 FAST fingerprinting verification, and instant digital badge generation.

3. FACILITY OPERATIONAL SPECIFICATIONS:
   - Primary Campus: {facility_name}
   - Loading Dock Ingress: {facility_address}
   - Shift Hours: Evening Janitorial (17:00 - 23:30) & Day Porter Services
   - Quality Standard: SigmaFidelity™ 95% hygiene audit threshold with automated Corrective Action Request (CAR) resolution.

Your executive credentials have been provisioned. You may access your dashboard at any time to monitor your on-site personnel and review compliance records.

Sincerely,

Humberto Dominguez, CEO
HWB Cleaning Services LLC
Dallas-Fort Worth Metropolitan Area
Phone: (214) 862-2300 | Web: mop.hwbcleaning.com
"""
                cur.execute("""
                    INSERT INTO "PendingOutbox" (recipient, subject, body, created_at, status)
                    VALUES (%s, %s, %s, CURRENT_DATE, 'PENDING')
                    RETURNING id;
                """, (contact_email, email_subject, email_body))
                outbox_id = cur.fetchone()["id"]
                print(f"  ✓ Staged welcome letter in PendingOutbox (ID: #{outbox_id})")
            result["outbox_id"] = outbox_id

            # 6. Record Milestone & Activity Log
            print(f"[6/6] Logging institutional milestone and activity stream...")
            cur.execute("""
                SELECT id FROM "Milestones" WHERE name = %s;
            """, (f"{company_name} Institutional Onboarding",))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO "Milestones" (category, name, status, description)
                    VALUES (%s, %s, 'Completed', %s);
                """, (
                    "Model C Partnerships",
                    f"{company_name} Institutional Onboarding",
                    f"Successfully provisioned white-label portal, LMS workspace, {facility_name} schedule, and compliance intake."
                ))

            cur.execute("""
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description, timestamp)
                VALUES (%s, 'Customer', 'PARTNER_PROVISIONED', %s, CURRENT_TIMESTAMP);
            """, (
                customer_id,
                f"{company_name} Model C partner infrastructure provisioned with {contract_number} {facility_name} schedule."
            ))
            print(f"  ✓ Institutional milestone and activity logged successfully.")

            conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"❌ Error during partner onboarding: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        raise e
    finally:
        conn.close()

    print(f"\n=======================================================")
    print(f"  ✓ Partner Onboarding Complete: {company_name}")
    print(f"  Customer ID: {result['customer_id']} | Tenant ID: {result['tenant_id']}")
    print(f"  WorkOrder ID: #{result['work_order_id']} | Outbox ID: #{result['outbox_id']}")
    print(f"=======================================================\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SigmaFidelity™ Partner Onboarding CLI")
    parser.add_argument("--name", default="Bosanna LLC", help="Partner company name")
    parser.add_argument("--slug", default="bosanna", help="Unique URL slug")
    parser.add_argument("--contact", default="Angelica Hudgins", help="Executive contact name")
    parser.add_argument("--email", default="ahudgins@bosanna.com", help="Executive email")
    parser.add_argument("--phone", default="(214) 862-2300", help="Executive phone")
    parser.add_argument("--contract", default="TIPS #260102", help="Prime contract identifier")
    parser.add_argument("--facility", default="Collin College Frisco Campus", help="Assigned facility name")
    parser.add_argument("--sqf", type=int, default=125000, help="Cleanable square footage")
    args = parser.parse_args()

    onboard_partner(
        company_name=args.name,
        slug=args.slug,
        contact_name=args.contact,
        contact_email=args.email,
        contact_phone=args.phone,
        contract_number=args.contract,
        facility_name=args.facility,
        sqf=args.sqf
    )
