#!/usr/bin/env python3
"""
SigmaFidelity™ Autonomous Corporate Umbrella Engine
HWB-QMS Standard: Unsupervised Lead Clustering & Enterprise Propagation
Author: George (Lead Systems Architect)
"""

import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """Establish connection to PostgreSQL using environment variable."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        sys.exit(1)
    return psycopg2.connect(db_url)


SEED_UMBRELLAS = [
    # 1. Commercial National Conglomerates & Franchises
    {
        "name": "KinderCare Learning Companies",
        "category": "National Conglomerate",
        "patterns": [
            "center_name ILIKE '%kindercare%'",
            "(center_name ILIKE '%champions%' AND (center_name ILIKE '%kce%' OR center_name ILIKE '%knowledge learning%' OR center_name ILIKE '%elementary%' OR center_name ILIKE '%kipp%' OR center_name ILIKE '%iltx%' OR center_name ILIKE '%isd%' OR center_name ILIKE '%school%' OR center_name ILIKE '%park%' OR center_name ILIKE '%mesquite%'))",
            "website ILIKE '%kindercare%'"
        ],
        "domains": ["kindercare.com", "discoverchampions.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Primrose Schools",
        "category": "Multi-Unit Franchise Hubs",
        "patterns": ["center_name ILIKE '%primrose%'", "website ILIKE '%primroseschools%'"],
        "domains": ["primroseschools.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "The Learning Experience",
        "category": "National Franchise",
        "patterns": ["center_name ILIKE '%learning experience%'", "website ILIKE '%thelearningexperience.com%'"],
        "domains": ["thelearningexperience.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Learning Care Group",
        "category": "Multi-Brand Conglomerate",
        "patterns": [
            "center_name ILIKE '%children%courtyard%'",
            "center_name ILIKE '%la petite%'",
            "center_name ILIKE '%everbrook%'",
            "center_name ILIKE '%tutor time%'",
            "center_name ILIKE '%childtime%'",
            "center_name ILIKE '%learning care group%'",
            "website ILIKE '%learningcaregroup%'"
        ],
        "domains": ["learningcaregroup.com", "lapetite.com", "childrenscourtyard.com", "everbrookacademy.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "The Goddard School",
        "category": "National Franchise",
        "patterns": ["center_name ILIKE '%goddard%'", "website ILIKE '%goddardschool%'"],
        "domains": ["goddardschool.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Kids 'R' Kids Learning Academies",
        "category": "Mega-Academy Franchise",
        "patterns": ["center_name ILIKE '%kids %r% kids%'", "center_name ILIKE '%kids r kids%'", "website ILIKE '%kidsrkids%'"],
        "domains": ["kidsrkids.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Children's Lighthouse",
        "category": "Multi-Unit Franchise",
        "patterns": ["center_name ILIKE '%children%lighthouse%'", "website ILIKE '%childrenslighthouse%'"],
        "domains": ["childrenslighthouse.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Kiddie Academy",
        "category": "National Franchise",
        "patterns": ["center_name ILIKE '%kiddie academy%'", "website ILIKE '%kiddieacademy%'"],
        "domains": ["kiddieacademy.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Childcare Network",
        "category": "National Consolidator",
        "patterns": ["center_name ILIKE '%childcare network%'", "website ILIKE '%childcarenetwork.com%'"],
        "domains": ["childcarenetwork.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Children's Learning Adventure",
        "category": "Resort Mega-Facilities",
        "patterns": ["center_name ILIKE '%children%learning adventure%'", "website ILIKE '%childrenslearningadventure%'"],
        "domains": ["childrenslearningadventure.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Crème de la Crème",
        "category": "Luxury Mega-Facilities",
        "patterns": ["center_name ILIKE '%cr_me de la cr_me%'", "center_name ILIKE '%creme de la creme%'", "website ILIKE '%cremedelacreme%'"],
        "domains": ["cremedelacreme.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Cadence Education",
        "category": "Private Equity Consolidator",
        "patterns": ["center_name ILIKE '%cadence academy%'", "center_name ILIKE '%cadence education%'", "website ILIKE '%cadence-education%'"],
        "domains": ["cadence-education.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Fractal Education Group",
        "category": "Private Equity Consolidator",
        "patterns": ["website ILIKE '%fractaleg%'", "website ILIKE '%fractal.education%'"],
        "domains": ["fractaleg.com", "fractal.education"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Spring Education Group",
        "category": "Multi-Brand Conglomerate",
        "patterns": ["website ILIKE '%springeducationgroup%'"],
        "domains": ["springeducationgroup.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Guidepost Montessori",
        "category": "National Holding Co.",
        "patterns": ["center_name ILIKE '%guidepost%'", "website ILIKE '%guidepostmontessori%'", "website ILIKE '%higherground%'"],
        "domains": ["guidepostmontessori.com", "higherground.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Bright Horizons",
        "category": "Corporate Childcare",
        "patterns": ["center_name ILIKE '%bright horizons%'", "website ILIKE '%brighthorizons%'"],
        "domains": ["brighthorizons.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Big Blue Marble Academy",
        "category": "Multi-State Consolidator",
        "patterns": ["center_name ILIKE '%big blue marble%'", "website ILIKE '%bbmacademy%'"],
        "domains": ["bbmacademy.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Little Sunshine's Playhouse",
        "category": "High-End Regional Hub",
        "patterns": ["center_name ILIKE '%little sunshine%playhouse%'", "center_name ILIKE 'LSP Stone Oak%'", "website ILIKE '%littlesunshine%'"],
        "domains": ["littlesunshine.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Stepping Stone School",
        "category": "Regional Network Hub",
        "patterns": ["center_name ILIKE 'Stepping Stone School%'", "website ILIKE '%steppingstoneschool.com%'"],
        "domains": ["steppingstoneschool.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Spanish Schoolhouse",
        "category": "Regional Immersion Network",
        "patterns": ["center_name ILIKE '%spanish schoolhouse%'", "website ILIKE '%spanishschoolhouse%'"],
        "domains": ["spanishschoolhouse.com"],
        "delivery_model": "Unknown"
    },

    # 2. Regional Commercial Mega-Chains
    {
        "name": "Country Home Learning Center",
        "category": "Regional Commercial Mega-Chain",
        "patterns": ["center_name ILIKE '%country home learning%'"],
        "domains": ["countryhomelearningcenter.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Little Tyke Learning Centers",
        "category": "Regional Commercial Chain",
        "patterns": ["center_name ILIKE '%little tyke%'"],
        "domains": ["littletyke.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Building Blocks Academy",
        "category": "Regional Commercial Chain",
        "patterns": ["center_name ILIKE '%building blocks%'"],
        "domains": ["buildingblocksacademy.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Bright Beginnings",
        "category": "Regional Commercial Chain",
        "patterns": ["center_name ILIKE '%bright beginnings%'"],
        "domains": [],
        "delivery_model": "Unknown"
    },

    # 3. Institutional Non-Profit & Municipal Networks
    {
        "name": "YMCA Child Care & Afterschool",
        "category": "Institutional Non-Profit Network",
        "patterns": ["center_name ILIKE '%ymca%'"],
        "domains": ["ymca.org", "ymcahouston.org", "ymcadallas.org", "austinymca.org", "ymcasatx.org"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Head Start & Community Action",
        "category": "Federal Institutional Early Childhood",
        "patterns": ["center_name ILIKE '%head start%'"],
        "domains": ["headstart.gov", "eclkc.ohs.acf.hhs.gov"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Right At School",
        "category": "School District Program Partner",
        "patterns": ["center_name ILIKE '%right at school%'"],
        "domains": ["rightatschool.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Camp Fire Kids Care",
        "category": "Non-Profit Youth Organization",
        "patterns": ["center_name ILIKE '%camp fire%'"],
        "domains": ["campfire.org"],
        "delivery_model": "Unknown"
    },
    {
        "name": "AlphaBEST Education",
        "category": "School District Program Partner",
        "patterns": ["center_name ILIKE '%alphabest%'", "website ILIKE '%alphabest.org%'"],
        "domains": ["alphabest.org"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Koala Kare",
        "category": "Regional School District Partner",
        "patterns": ["center_name ILIKE '%koala kare%'"],
        "domains": [],
        "delivery_model": "Unknown"
    },
    {
        "name": "After Hour Kid Power",
        "category": "Regional School District Partner",
        "patterns": ["center_name ILIKE '%after hour kid power%'"],
        "domains": [],
        "delivery_model": "Unknown"
    },
    {
        "name": "Upbring Head Start",
        "category": "Regional Non-Profit",
        "patterns": ["center_name ILIKE '%upbring head start%'"],
        "domains": ["upbring.org"],
        "delivery_model": "Unknown"
    },

    # 4. Faith-Based & Church-Partnered Networks
    {
        "name": "Lionheart Children's Academy",
        "category": "Non-Profit Church Network",
        "patterns": ["center_name ILIKE '%lionheart%'", "website ILIKE '%lionheartkid%'"],
        "domains": ["lionheartkid.org"],
        "delivery_model": "Unknown"
    },
    {
        "name": "The Pillars Christian Learning Center",
        "category": "Church-Partnered Network",
        "patterns": ["center_name ILIKE '%pillars christian%'", "website ILIKE '%thepillarsclc%'"],
        "domains": ["thepillarsclc.com"],
        "delivery_model": "Unknown"
    },
    {
        "name": "The Academy at Craig Ranch",
        "category": "Church-Partnered Academy",
        "patterns": ["center_name ILIKE '%academy at craig ranch%'", "website ILIKE '%academyatcraigranch%'"],
        "domains": ["academyatcraigranch.org"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Baptist Weekday Ministries",
        "category": "Denominational Church Network",
        "patterns": ["center_name ILIKE '%baptist%'"],
        "domains": ["texasbaptists.org"],
        "delivery_model": "Unknown"
    },
    {
        "name": "United Methodist Day Schools",
        "category": "Denominational Church Network",
        "patterns": ["center_name ILIKE '%methodist%'"],
        "domains": ["txcumc.org"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Lutheran Day Schools",
        "category": "Parochial Church Network",
        "patterns": ["center_name ILIKE '%lutheran%'"],
        "domains": [],
        "delivery_model": "Unknown"
    },
    {
        "name": "Presbyterian Early Learning",
        "category": "Denominational Church Network",
        "patterns": ["center_name ILIKE '%presbyterian%'"],
        "domains": [],
        "delivery_model": "Unknown"
    },
    {
        "name": "Episcopal Day Schools",
        "category": "Parochial Church Network",
        "patterns": ["center_name ILIKE '%episcopal%'"],
        "domains": [],
        "delivery_model": "Unknown"
    },

    # 5. Public Charter School Pre-K Networks
    {
        "name": "IDEA Public Schools Pre-K",
        "category": "Public Charter School Network",
        "patterns": ["center_name ILIKE 'idea %'", "center_name ILIKE '%idea public school%'"],
        "domains": ["ideapublicschools.org"],
        "delivery_model": "Unknown"
    },
    {
        "name": "Uplift Education",
        "category": "Public Charter School Network",
        "patterns": ["center_name ILIKE '%uplift%'"],
        "domains": ["uplifteducation.org"],
        "delivery_model": "Unknown"
    }
]


def seed_corporate_umbrellas(conn) -> None:
    """Initialize or update known umbrella definitions in the registry table."""
    cur = conn.cursor()
    for item in SEED_UMBRELLAS:
        cur.execute("""
            INSERT INTO "CorporateUmbrellas" (
                umbrella_name, category, matching_patterns, root_domains, cleaning_delivery_model
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (umbrella_name) DO UPDATE SET
                category = EXCLUDED.category,
                matching_patterns = EXCLUDED.matching_patterns,
                root_domains = EXCLUDED.root_domains;
        """, (
            item["name"],
            item["category"],
            item["patterns"],
            item["domains"],
            item["delivery_model"]
        ))
    conn.commit()
    cur.close()
    print(f"[SEEDED] {len(SEED_UMBRELLAS)} corporate umbrella definitions verified in registry.")


def execute_propagation(conn) -> Tuple[int, int, float]:
    """Classify leads against the dynamic CorporateUmbrellas registry."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT id, umbrella_name, matching_patterns, root_domains, cleaning_delivery_model FROM "CorporateUmbrellas"')
    umbrellas = cur.fetchall()

    total_tagged = 0
    total_cap = 0
    total_val = 0.0

    for u in umbrellas:
        u_name = u["umbrella_name"]
        escaped_name = u_name.replace("'", "''")
        patterns = u["matching_patterns"] or []
        domains = u["root_domains"] or []

        clauses = []
        for p in patterns:
            clauses.append(f"({p})")
        for d in domains:
            clauses.append(f"(website ILIKE '%{d}%')")

        if not clauses:
            continue

        combined_condition = " OR ".join(clauses)
        update_sql = f"""
            UPDATE "Leads"
            SET umbrella_name = '{escaped_name}',
                cleaning_delivery_model = COALESCE(cleaning_delivery_model, '{u["cleaning_delivery_model"]}')
            WHERE ({combined_condition})
              AND (umbrella_name IS NULL OR umbrella_name = '')
            RETURNING id, capacity, estimated_annual_value;
        """
        cur.execute(update_sql)
        rows = cur.fetchall()
        count = len(rows)
        sub_cap = sum(r["capacity"] or 0 for r in rows)
        sub_val = sum(r["estimated_annual_value"] or 0.0 for r in rows)

        total_tagged += count
        total_cap += sub_cap
        total_val += sub_val

        if count > 0:
            print(f"-> [CLASSIFIED] {u_name:<34}: {count:>3} campuses | Cap: {sub_cap:>6} | Est. Value: ${sub_val:>12,.2f}")

    # Synchronize umbrella stats back to CorporateUmbrellas table
    cur.execute("""
        UPDATE "CorporateUmbrellas" u
        SET campus_count = sub.cnt,
            total_capacity = sub.tot_cap,
            estimated_annual_value = sub.tot_val,
            updated_at = CURRENT_TIMESTAMP
        FROM (
            SELECT umbrella_name, COUNT(*) as cnt, SUM(capacity) as tot_cap, SUM(estimated_annual_value) as tot_val
            FROM "Leads"
            WHERE umbrella_name IS NOT NULL AND umbrella_name != ''
            GROUP BY umbrella_name
        ) sub
        WHERE u.umbrella_name = sub.umbrella_name;
    """)

    conn.commit()
    cur.close()
    return total_tagged, total_cap, total_val


def discover_unsupervised_clusters(conn, min_campuses: int = 3) -> List[Dict]:
    """Mine unclassified child care records for recurring corporate stems."""
    cur = conn.cursor()
    cur.execute("""
        SELECT center_name, city, capacity, estimated_annual_value, website
        FROM "Leads"
        WHERE (umbrella_name IS NULL OR umbrella_name = '')
          AND (process_id LIKE 'texas-ccl-%' OR lead_source = 'Texas CCL API')
    """)
    rows = cur.fetchall()

    stopwords = {
        'the', 'inc', 'llc', 'center', 'child', 'care', 'learning', 'academy', 
        'preschool', 'school', 'daycare', 'early', 'childhood', 'development', 
        'children', 'childrens', 'kids', 'dba', 'of', 'and', '&', 
        'at', 'in', 'for', 'little', 'montessori', 'family', 'prep', 'preparatory',
        'church', 'baptist', 'methodist', 'presbyterian', 'lutheran', 'episcopal'
    }

    def extract_stem(name: str) -> str:
        if 'dba' in name.lower():
            name = re.split(r'\bdba\b', name, flags=re.IGNORECASE)[-1]
        tokens = re.findall(r'[a-zA-Z]{3,}', name.lower())
        meaningful = [t for t in tokens if t not in stopwords]
        return ' '.join(meaningful[:2]) if len(meaningful) >= 1 else ''

    stems: Dict[str, Dict] = {}
    for r in rows:
        name, city, cap, val, web = r
        stem = extract_stem(name)
        if len(stem) >= 3:
            if stem not in stems:
                stems[stem] = {'count': 0, 'cap': 0, 'val': 0.0, 'samples': set(), 'cities': set()}
            stems[stem]['count'] += 1
            stems[stem]['cap'] += (cap or 0)
            stems[stem]['val'] += (val or 0.0)
            stems[stem]['samples'].add(name.strip())
            if city:
                stems[stem]['cities'].add(city.strip())

    discovered = []
    for stem, meta in stems.items():
        if meta['count'] >= min_campuses and len(meta['cities']) >= 2:
            discovered.append({
                "stem": stem,
                "count": meta["count"],
                "capacity": meta["cap"],
                "value": meta["val"],
                "samples": list(meta["samples"])[:3],
                "cities": list(meta["cities"])[:3]
            })

    discovered.sort(key=lambda x: x["value"], reverse=True)
    cur.close()
    return discovered


def run_engine():
    """Main execution entry point."""
    conn = get_db_connection()
    print("================================================================================")
    print("🧬  SigmaFidelity™ Autonomous Corporate Umbrella Learning Engine")
    print("================================================================================")
    
    seed_corporate_umbrellas(conn)
    tagged, cap, val = execute_propagation(conn)
    print(f"[PROPAGATION] Leads Tagged: {tagged} | Added Capacity: {cap:,} | Added Value: ${val:,.2f}")

    candidates = discover_unsupervised_clusters(conn, min_campuses=3)
    print(f"[AUTONOMOUS DISCOVERY] Identified {len(candidates)} candidate multi-facility clusters.")
    for cand in candidates[:5]:
        print(f"   -> Stem: '{cand['stem']:<18}' | Campuses: {cand['count']:>2} | Cap: {cand['capacity']:>5} | Pipeline: ${cand['value']:>10,.2f}")
        print(f"      Samples: {cand['samples'][:2]}")

    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(DISTINCT umbrella_name), COUNT(*), SUM(capacity), SUM(estimated_annual_value)
        FROM "Leads"
        WHERE umbrella_name IS NOT NULL AND umbrella_name != '';
    """)
    u_count, l_count, total_cap, total_val = cur.fetchone()
    print("================================================================================")
    print(f"ACTIVE UMBRELLA PORTFOLIO: {u_count} Networks | {l_count} Campuses | {total_cap:,} Children | ${total_val:,.2f}/yr")
    print("================================================================================")
    cur.close()
    conn.close()


if __name__ == "__main__":
    run_engine()
