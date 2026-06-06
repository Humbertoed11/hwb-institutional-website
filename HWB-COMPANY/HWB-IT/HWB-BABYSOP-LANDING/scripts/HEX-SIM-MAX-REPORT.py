"""
HEX-SIM-MAX-REPORT.py
System simulation script for compiling L10 JBREC-Max Feasibility Reports.
Ensures rigorous calculation of price equalization and document rendering.
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Any, List

# Define DB URL default and target reports directory
DB_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db"
)

REPORTS_DIR: str = (
    "/app/HEX-DATA/REPORTS"
    if os.path.exists("/app")
    else "/home/humbertoed/hexgrowth/HEX-DATA/REPORTS"
)


def fetch_simulation_data(project_id: int) -> Dict[str, Any]:
    """
    Fetches the project details, cognitive bridge parameters, and active
    system state weights required to generate the feasibility report.
    """
    conn = psycopg2.connect(DB_URL)
    data: Dict[str, Any] = {}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Fetch project data
            cur.execute(
                'SELECT * FROM "HEX_Projects" WHERE id = %s;', (project_id,)
            )
            project = cur.fetchone()
            if not project:
                raise ValueError(f"Project ID {project_id} not found in database.")
            data["project"] = dict(project)

            # 2. Fetch parameters from Cognitive Bridge
            cur.execute(
                'SELECT parameter_name, parameter_value FROM "HEX_CognitiveBridge";'
            )
            bridge_rows = cur.fetchall()
            bridge_params = {
                row["parameter_name"]: float(row["parameter_value"])
                for row in bridge_rows
            }
            data["bridge_params"] = bridge_params

            # 3. Fetch weights from SystemState
            session_id = "2026-06-04-INTELLIGENT-LEGEND-COMPLETED"
            cur.execute(
                'SELECT state_data FROM "HEX_SystemState" WHERE session_id = %s;',
                (session_id,),
            )
            state_row = cur.fetchone()
            active_weights: Dict[str, str] = {}
            if state_row:
                state_data = state_row["state_data"]
                if isinstance(state_data, str):
                    state_data = json.loads(state_data)
                params = state_data.get("parameters", {})
                for k, v in params.items():
                    if k.startswith("Weight: "):
                        lobe_name = (
                            k.replace("Weight: ", "")
                            .replace("_weight", "")
                            .upper()
                        )
                        active_weights[lobe_name] = str(v)
            
            if not active_weights:
                active_weights = {
                    "L1_ZONING": "0.1500 (Baseline)",
                    "L2_TRANSIT": "0.1000 (Baseline)",
                    "L3_POWER": "0.1500 (Baseline)",
                    "L4_LEGAL": "0.1500 (Baseline)",
                    "L5_RANGER": "0.1000 (Baseline)",
                    "L6_PULSE": "0.0500 (Baseline)",
                    "L7_FINANCE": "0.2000 (Baseline)",
                    "L8_INFERENCE": "0.1000 (Baseline)"
                }
            data["active_weights"] = active_weights
    finally:
        conn.close()
    return data


def calculate_pricing_matrix(
    project: Dict[str, Any], bridge_params: Dict[str, float]
) -> List[Dict[str, Any]]:
    """
    Computes equalized pricing matrix based on targeted IRR and interest rates.
    """
    interest_rate: float = bridge_params.get("interest_rate", 0.055)
    target_irr: float = float(project.get("target_irr") or 15.0)
    
    # Calculate baseline multiplier B
    base_b: float = 400000.0 * (1.0 + (target_irr - 15.0) / 100.0)

    lot_configurations: List[Dict[str, Any]] = [
        {
            "lot_size": "30' Alley",
            "detail": "Alley loaded detached SFD",
            "sqft": 1272,
            "mult": 0.70,
            "absorption": "4.0",
        },
        {
            "lot_size": "35' Alley",
            "detail": "Alley loaded detached SFD",
            "sqft": 1614,
            "mult": 0.78,
            "absorption": "4.0",
        },
        {
            "lot_size": "40' Front",
            "detail": "Front loaded detached SFD",
            "sqft": 1825,
            "mult": 0.85,
            "absorption": "3.0",
        },
        {
            "lot_size": "50' Front",
            "detail": "Front loaded detached SFD",
            "sqft": 2175,
            "mult": 1.00,
            "absorption": "3.0",
        },
        {
            "lot_size": "55' Front",
            "detail": "Front loaded detached SFD",
            "sqft": 2525,
            "mult": 1.08,
            "absorption": "2.5",
        },
        {
            "lot_size": "60' Front",
            "detail": "Front loaded detached SFD",
            "sqft": 2725,
            "mult": 1.20,
            "absorption": "2.0",
        },
        {
            "lot_size": "70' Front",
            "detail": "Front loaded detached SFD",
            "sqft": 3275,
            "mult": 1.40,
            "absorption": "1.5",
        },
    ]

    r: float = interest_rate + 0.015
    monthly_rate: float = r / 12.0
    n_payments: int = 360
    pi_factor: float = (
        (monthly_rate * (1 + monthly_rate) ** n_payments)
        / (((1 + monthly_rate) ** n_payments) - 1)
    )

    pricing_matrix: List[Dict[str, Any]] = []
    for config in lot_configurations:
        base_price: int = int(base_b * config["mult"])
        pi: float = base_price * 0.90 * pi_factor
        taxes: float = (base_price * 0.0282) / 12.0
        hoa: float = 105.0
        monthly_cto: int = int(pi + taxes + hoa)
        qualifying_income: int = int((monthly_cto / 0.33) * 12.0)

        pricing_matrix.append(
            {
                "lot_size": config["lot_size"],
                "detail": config["detail"],
                "sqft": config["sqft"],
                "base_price": base_price,
                "monthly_cto": monthly_cto,
                "qualifying_income": qualifying_income,
                "absorption": config["absorption"],
            }
        )

    return pricing_matrix


def compile_report_max_simulation(project_id: int) -> str:
    """
    Compiles the HTML Max Feasibility Report using the Jinja template
    and simulation datasets. Returns the absolute path of the generated HTML.
    """
    print(
        f"[SIM] Initiating compilation for Max Report. Project ID: {project_id}"
    )
    sim_data = fetch_simulation_data(project_id)
    project = sim_data["project"]
    bridge_params = sim_data["bridge_params"]
    active_weights = sim_data["active_weights"]

    pricing_matrix = calculate_pricing_matrix(project, bridge_params)

    # Setup Jinja Environment to load the template
    template_dir = (
        "/app/templates"
        if os.path.exists("/app/templates")
        else "/home/humbertoed/hexgrowth/app/templates"
    )
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("market_report_max.html")

    # Render template with context variables
    rendered_html = template.render(
        project=project,
        interest_rate=bridge_params.get("interest_rate", 0.055),
        cap_rate_baseline=bridge_params.get("cap_rate_baseline", 0.0725),
        permit_latency_days=bridge_params.get("permit_latency_days", 120.0),
        egress_speed_mph=bridge_params.get("egress_speed_mph", 45.0),
        construction_cost_index=bridge_params.get(
            "construction_cost_index", 1.15
        ),
        pricing_matrix=pricing_matrix,
        active_weights=active_weights,
    )

    os.makedirs(REPORTS_DIR, exist_ok=True)
    out_filename = f"HEX-SIM-MAX-REPORT-{project_id}.html"
    out_path = os.path.join(REPORTS_DIR, out_filename)

    with open(out_path, "w", encoding="utf-8") as file_out:
        file_out.write(rendered_html)

    print(f"SUCCESS: Simulated Max Report compiled at: {out_path}")
    return out_path


if __name__ == "__main__":
    import sys
    proj_id = 1
    if len(sys.argv) > 1:
        try:
            proj_id = int(sys.argv[1])
        except ValueError:
            pass
    compile_report_max_simulation(proj_id)
