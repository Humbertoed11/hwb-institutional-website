#!/usr/bin/env python3
"""
SigmaFidelity™ Enterprise Lead Classifier
HWB-QMS Standard: Multi-Unit Corporate Umbrella Ingestion
Author: George (Lead Systems Architect)
"""

import os
import sys
from typing import Dict, List, Tuple
import psycopg2


def get_db_connection():
    """Establish connection to PostgreSQL using environment variable."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        sys.exit(1)
    return psycopg2.connect(db_url)


def run_umbrella_tagging() -> None:
    """Classify and tag all identified multi-unit Texas daycares with their corporate umbrella."""
    conn = get_db_connection()
    cur = conn.cursor()

    networks: List[Tuple[str, str]] = [
        (
            "Learning Care Group",
            """(
                center_name ILIKE '%children%courtyard%'
                OR center_name ILIKE '%la petite%'
                OR center_name ILIKE '%everbrook%'
                OR center_name ILIKE '%tutor time%'
                OR center_name ILIKE '%childtime%'
                OR center_name ILIKE '%learning care group%'
                OR website ILIKE '%learningcaregroup%'
            )"""
        ),
        (
            "KinderCare Learning Companies",
            """(
                center_name ILIKE '%kindercare%'
                OR (center_name ILIKE '%champions%' AND (
                    center_name ILIKE '%kce%' OR
                    center_name ILIKE '%knowledge learning%' OR
                    center_name ILIKE '%elementary%' OR
                    center_name ILIKE '%kipp%' OR
                    center_name ILIKE '%iltx%' OR
                    center_name ILIKE '%isd%' OR
                    center_name ILIKE '%school%' OR
                    center_name ILIKE '%park%' OR
                    center_name ILIKE '%mesquite%'
                ))
                OR website ILIKE '%kindercare%'
            )"""
        ),
        (
            "Primrose Schools",
            """(
                center_name ILIKE '%primrose%'
                OR website ILIKE '%primroseschools%'
            )"""
        ),
        (
            "The Goddard School",
            """(
                center_name ILIKE '%goddard%'
                OR website ILIKE '%goddardschool%'
            )"""
        ),
        (
            "Kids 'R' Kids Learning Academies",
            """(
                center_name ILIKE '%kids %r% kids%'
                OR center_name ILIKE '%kids r kids%'
                OR website ILIKE '%kidsrkids%'
            )"""
        ),
        (
            "Children's Lighthouse",
            """(
                center_name ILIKE '%children%lighthouse%'
                OR website ILIKE '%childrenslighthouse%'
            )"""
        ),
        (
            "Kiddie Academy",
            """(
                center_name ILIKE '%kiddie academy%'
                OR website ILIKE '%kiddieacademy%'
            )"""
        ),
        (
            "Stepping Stone School",
            """(
                center_name ILIKE 'Stepping Stone School%'
                OR website ILIKE '%steppingstoneschool.com%'
            )"""
        ),
        (
            "Spanish Schoolhouse",
            """(
                center_name ILIKE '%spanish schoolhouse%'
                OR website ILIKE '%spanishschoolhouse%'
            )"""
        ),
        (
            "Cadence Education",
            """(
                center_name ILIKE '%cadence academy%'
                OR center_name ILIKE '%cadence education%'
                OR website ILIKE '%cadence-education%'
            )"""
        ),
        (
            "Guidepost Montessori",
            """(
                center_name ILIKE '%guidepost%'
                OR website ILIKE '%guidepostmontessori%'
                OR website ILIKE '%higherground%'
            )"""
        ),
        (
            "Crème de la Crème",
            """(
                center_name ILIKE '%cr_me de la cr_me%'
                OR center_name ILIKE '%creme de la creme%'
                OR website ILIKE '%cremedelacreme%'
            )"""
        ),
        (
            "Bright Horizons",
            """(
                center_name ILIKE '%bright horizons%'
                OR website ILIKE '%brighthorizons%'
            )"""
        ),
        (
            "Big Blue Marble Academy",
            """(
                center_name ILIKE '%big blue marble%'
                OR website ILIKE '%bbmacademy%'
            )"""
        ),
        (
            "Little Sunshine's Playhouse",
            """(
                (center_name ILIKE '%little sunshine%playhouse%' OR center_name ILIKE 'LSP Stone Oak%')
                OR website ILIKE '%littlesunshine%'
            )"""
        ),
        (
            "Children's Learning Adventure",
            """(
                center_name ILIKE '%children%learning adventure%'
                OR website ILIKE '%childrenslearningadventure%'
            )"""
        ),
    ]

    print("================================================================================")
    print("🏛️  SigmaFidelity™ Multi-Unit Lead Classifier Execution")
    print("================================================================================")

    total_tagged = 0
    total_val = 0.0
    total_cap = 0

    for umbrella_name, condition_sql in networks:
        escaped_name = umbrella_name.replace("'", "''")
        update_query = f"""
            UPDATE "Leads"
            SET umbrella_name = '{escaped_name}',
                cleaning_delivery_model = COALESCE(cleaning_delivery_model, 'Unknown')
            WHERE {condition_sql}
              AND (umbrella_name IS NULL OR umbrella_name = '')
            RETURNING id, capacity, estimated_annual_value;
        """
        cur.execute(update_query)
        rows = cur.fetchall()
        count = len(rows)
        sub_cap = sum(r[1] or 0 for r in rows)
        sub_val = sum(r[2] or 0.0 for r in rows)

        total_tagged += count
        total_cap += sub_cap
        total_val += sub_val

        print(f"-> [CLASSIFIED] {umbrella_name:<32}: {count:>3} campuses | Cap: {sub_cap:>6} | Est. Value: ${sub_val:>12,.2f}")

    conn.commit()

    cur.execute("""
        SELECT COUNT(*), SUM(capacity), SUM(estimated_annual_value)
        FROM "Leads"
        WHERE umbrella_name IS NOT NULL AND umbrella_name != '';
    """)
    overall_count, overall_cap, overall_val = cur.fetchone()

    print("================================================================================")
    print(f"TOTAL NEWLY TAGGED: {total_tagged} campuses | Cap: {total_cap:,} | Pipeline: ${total_val:,.2f}")
    print(f"CUMULATIVE UMBRELLA PIPELINE: {overall_count} campuses | Cap: {overall_cap:,} | Pipeline: ${overall_val:,.2f}")
    print("================================================================================")

    cur.close()
    conn.close()


if __name__ == "__main__":
    run_umbrella_tagging()
