#!/usr/bin/env python3
"""
SigmaFidelity™ Memory Rot & Context Health Meter
Standard: HWB-QMS-11.7 (Cognitive Load & Context Integrity)
Responsibility: George (Systems Architect) & Peter (Recovery Specialist)

Empirically measures:
1. Context Bloat (Transcript bytes, tool noise vs signal ratio)
2. Attention Dilution (Sequence saturation and attention distribution decay)
3. "Lost in the Middle" Risk (Dead-zone stranded instructions in the middle 70%)
4. Context / Instruction Drift (Governance compliance, 3rd-person adherence, format fidelity)
5. Composite Context Rot Index & Session Restart Recommendation
"""

import os
import sys
import glob
import json
import math
import re
from datetime import datetime
from typing import Dict, Any, List, Tuple


def find_latest_transcript_dir() -> str:
    """Auto-detects the most active conversation directory under ~/.gemini/antigravity-cli/brain/."""
    brain_dir = os.path.expanduser("~/.gemini/antigravity-cli/brain")
    if not os.path.exists(brain_dir):
        return ""
    candidates = []
    for entry in os.listdir(brain_dir):
        full_p = os.path.join(brain_dir, entry)
        if os.path.isdir(full_p) and not entry.startswith('.'):
            log_p = os.path.join(full_p, ".system_generated", "logs", "transcript.jsonl")
            if os.path.exists(log_p):
                candidates.append((full_p, os.path.getmtime(log_p)))
    if not candidates:
        return ""
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


def render_bar(score: float, width: int = 24) -> str:
    """Renders a high-fidelity visual progress bar."""
    filled = int(round((score / 100.0) * width))
    filled = max(0, min(width, filled))
    empty = width - filled
    
    if score < 35:
        color = "\033[32m"  # Green
    elif score < 65:
        color = "\033[33m"  # Yellow
    elif score < 80:
        color = "\033[38;5;208m"  # Orange
    else:
        color = "\033[31m"  # Red
    reset = "\033[0m"
    
    bar = f"{color}[{'█' * filled}{'░' * empty}] {score:5.1f}%{reset}"
    return bar


def analyze_transcript(transcript_path: str) -> Dict[str, Any]:
    """Parses transcript.jsonl and calculates memory health metrics."""
    if not os.path.exists(transcript_path):
        raise FileNotFoundError(f"Transcript log not found at: {transcript_path}")

    file_size_bytes = os.path.getsize(transcript_path)
    file_size_mb = file_size_bytes / (1024 * 1024)

    total_steps = 0
    user_inputs: List[Tuple[int, str]] = []
    model_responses: List[Tuple[int, str]] = []
    tool_calls_count = 0
    tool_output_bytes = 0
    model_content_bytes = 0
    user_content_bytes = 0

    with open(transcript_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            total_steps += 1
            try:
                data = json.loads(line)
            except Exception:
                continue

            step_idx = data.get('step_index', total_steps)
            source = data.get('source', '')
            step_type = data.get('type', '')
            content = data.get('content', '') or ''
            tool_calls = data.get('tool_calls', [])

            if step_type == 'USER_INPUT' or source == 'USER_EXPLICIT':
                user_inputs.append((step_idx, content))
                user_content_bytes += len(content)
            elif step_type == 'PLANNER_RESPONSE' or source == 'MODEL':
                if content:
                    model_responses.append((step_idx, content))
                    model_content_bytes += len(content)
                if tool_calls:
                    tool_calls_count += len(tool_calls)
            elif step_type == 'GENERIC':
                tool_output_bytes += len(content)

    if total_steps == 0:
        return {"error": "Transcript is empty"}

    # 1. CONTEXT BLOAT SCORE (0 - 100)
    # Calibrated against industrial saturation: 2MB ~ 30%, 10MB ~ 70%, 20MB+ ~ 95%
    size_factor = min(100.0, (file_size_mb / 20.0) * 100.0)
    steps_factor = min(100.0, (total_steps / 10000.0) * 100.0)
    
    # Noise ratio (tool outputs vs meaningful conversational text)
    meaningful_bytes = model_content_bytes + user_content_bytes
    noise_ratio = (tool_output_bytes / (tool_output_bytes + meaningful_bytes)) if (tool_output_bytes + meaningful_bytes) > 0 else 0.5
    noise_factor = noise_ratio * 100.0

    bloat_score = (0.45 * size_factor) + (0.35 * steps_factor) + (0.20 * noise_factor)
    bloat_score = min(100.0, max(0.0, bloat_score))

    # 2. ATTENTION DILUTION SCORE (0 - 100)
    # Mathematical transformer attention dispersion over N steps
    # Standard attention dispersion models indicate focus degrades asymptotically as N grows beyond 1,500 turns
    dilution_raw = 1.0 - (1.0 / (1.0 + (total_steps / 2200.0) ** 0.85))
    dilution_score = min(100.0, max(0.0, dilution_raw * 100.0))

    # 3. "LOST IN THE MIDDLE" RISK SCORE (0 - 100)
    # U-shaped curve: First 15% (head) and last 15% (tail) have high recall
    # Middle 70% is the dead zone
    head_cutoff = int(total_steps * 0.15)
    tail_cutoff = int(total_steps * 0.85)

    middle_user_inputs = [idx for idx, _ in user_inputs if head_cutoff <= idx <= tail_cutoff]
    middle_ratio = len(middle_user_inputs) / len(user_inputs) if user_inputs else 0.0

    # Risk scales with the depth of the middle zone and how many user requirements are buried
    middle_depth_factor = min(100.0, (len(middle_user_inputs) / 50.0) * 100.0)
    lost_middle_score = (0.60 * (middle_ratio * 100.0)) + (0.40 * middle_depth_factor)
    lost_middle_score = min(100.0, max(0.0, lost_middle_score))

    # 4. CONTEXT / INSTRUCTION DRIFT SCORE (0 - 100)
    # Analyze the last 15 model responses for institutional standard compliance
    recent_responses = model_responses[-15:] if len(model_responses) >= 15 else model_responses
    drift_violations = 0
    total_checks = 0

    first_person_patterns = [
        r'\bI\b', r'\bwe\b', r'\bmy\b', r'\bour\b', r'\bme\b', r'\bus\b'
    ]

    for _, resp in recent_responses:
        # Check 1: First-person pronoun leakage (Governance Section 1.2)
        total_checks += 1
        has_first_person = any(re.search(pat, resp, re.IGNORECASE) for pat in first_person_patterns)
        if has_first_person:
            drift_violations += 1

        # Check 2: Terminal format hierarchy (HWB-QMS-11.2 - Emojis & Bold Headers)
        total_checks += 1
        has_high_fidelity = bool(re.search(r'(🏛️|🛠️|📡|🧠|###|\*\*Executive Summary|\*\*Technical Implementation)', resp))
        if not has_high_fidelity:
            drift_violations += 0.5

    drift_rate = (drift_violations / total_checks) if total_checks > 0 else 0.0
    drift_score = min(100.0, max(0.0, drift_rate * 100.0))

    # 5. COMPOSITE CONTEXT ROT INDEX (0 - 100)
    # Weighted composite: Bloat (30%), Dilution (25%), Lost-in-Middle (25%), Drift (20%)
    rot_index = (
        0.30 * bloat_score +
        0.25 * dilution_score +
        0.25 * lost_middle_score +
        0.20 * drift_score
    )
    rot_index = min(100.0, max(0.0, rot_index))

    # Determine status & recommendation
    if rot_index < 35.0:
        status_label = "PRISTINE / OPTIMAL FOCUS"
        status_badge = "🟢 GREEN"
        recommendation = "Session is crisp and healthy. Working memory is operating with high attention fidelity."
    elif rot_index < 65.0:
        status_label = "MODERATE WEAR / NOTICEABLE DILUTION"
        status_badge = "🟡 YELLOW"
        recommendation = "Attention spread is growing. Avoid dumping massive terminal logs into chat. Keep edits surgical."
    elif rot_index < 80.0:
        status_label = "HIGH CONTEXT ROT / ATTENTION SATURATION"
        status_badge = "🟠 ORANGE"
        recommendation = "Context is heavily populated. Run Peter's shadow snapshot, verify HWB-SESSION-RECOVERY.md, and plan a restart soon."
    else:
        status_label = "CRITICAL SATURATION / IMMEDIATE RESTART MANDATED"
        status_badge = "🔴 RED ALERT"
        recommendation = "Working memory has exceeded optimal cognitive bounds. Memory flush and session restart recommended immediately to reclaim maximum reasoning velocity."

    return {
        "rot_index": round(rot_index, 1),
        "status_label": status_label,
        "status_badge": status_badge,
        "recommendation": recommendation,
        "metrics": {
            "bloat": {
                "score": round(bloat_score, 1),
                "file_size_mb": round(file_size_mb, 2),
                "total_steps": total_steps,
                "tool_calls": tool_calls_count,
                "noise_ratio_pct": round(noise_ratio * 100, 1)
            },
            "dilution": {
                "score": round(dilution_score, 1),
                "steps": total_steps,
                "attention_retention_est": round(100.0 - dilution_score, 1)
            },
            "lost_in_middle": {
                "score": round(lost_middle_score, 1),
                "total_user_directives": len(user_inputs),
                "middle_zone_stranded": len(middle_user_inputs),
                "middle_ratio_pct": round(middle_ratio * 100, 1)
            },
            "drift": {
                "score": round(drift_score, 1),
                "inspected_responses": len(recent_responses),
                "governance_compliance_pct": round((1.0 - drift_rate) * 100, 1)
            }
        }
    }


def print_dashboard(data: Dict[str, Any], conv_id: str):
    """Outputs the High-Fidelity Terminal Meter."""
    rot = data["rot_index"]
    m = data["metrics"]
    
    print("\n" + "=" * 76)
    print("      🧠  SIGMAFIDELITY™ CONTEXT ROT & MEMORY HEALTH METER  🧠      ")
    print("              Standard: HWB-QMS-11.7 (Cognitive Integrity)           ")
    print("=" * 76)
    print(f" Conversation ID : {conv_id}")
    print(f" Telemetry Stamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S CST')}")
    print(f" Overall Status  : {data['status_badge']} — {data['status_label']}")
    print("-" * 76)
    print(f" TOTAL CONTEXT ROT INDEX : {render_bar(rot, 32)}")
    print("-" * 76)
    print(f" 1. Context Bloat       : {render_bar(m['bloat']['score'])}")
    print(f"    └─ Transcript Size  : {m['bloat']['file_size_mb']} MB across {m['bloat']['total_steps']:,} steps")
    print(f"    └─ Tool Executions  : {m['bloat']['tool_calls']:,} calls ({m['bloat']['noise_ratio_pct']}% raw tool output volume)")
    print()
    print(f" 2. Attention Dilution  : {render_bar(m['dilution']['score'])}")
    print(f"    └─ Attention Spread : Focus spread across {m['dilution']['steps']:,} steps")
    print(f"    └─ Effective Focus  : ~{m['dilution']['attention_retention_est']}% of baseline focus power remaining")
    print()
    print(f" 3. Lost-in-Middle Risk : {render_bar(m['lost_in_middle']['score'])}")
    print(f"    └─ Directives Total : {m['lost_in_middle']['total_user_directives']} user commands logged")
    print(f"    └─ Stranded in Mid  : {m['lost_in_middle']['middle_zone_stranded']} directives ({m['lost_in_middle']['middle_ratio_pct']}%) in the middle dead zone")
    print()
    print(f" 4. Instruction Drift   : {render_bar(m['drift']['score'])}")
    print(f"    └─ Governance Score : {m['drift']['governance_compliance_pct']}% compliance across recent {m['drift']['inspected_responses']} responses")
    print(f"    └─ Rule Fidelity    : 3rd Person & High-Fidelity Terminal Standard")
    print("-" * 76)
    print(f" 💡 RECOMMENDATION:")
    print(f"    {data['recommendation']}")
    print("=" * 76 + "\n")


def record_memory_rot_to_db(db_url: str = None) -> Dict[str, Any]:
    """Analyzes latest transcript and persists live Rack 1 snapshot into RackTelemetryHistory in PostgreSQL."""
    import psycopg2
    from psycopg2.extras import Json
    
    target_url = db_url or os.environ.get('DATABASE_URL', 'postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db')
    conv_dir = find_latest_transcript_dir()
    if not conv_dir or not os.path.exists(conv_dir):
        return {"status": "error", "message": "Could not locate active conversation directory"}
    
    conv_id = os.path.basename(conv_dir)
    transcript_p = os.path.join(conv_dir, ".system_generated", "logs", "transcript.jsonl")
    data = analyze_transcript(transcript_p)
    if "error" in data:
        return {"status": "error", "message": data["error"]}
    
    rot = data["rot_index"]
    m = data["metrics"]
    bloat = m["bloat"]["score"]
    
    conn = psycopg2.connect(target_url)
    try:
        with conn.cursor() as cur:
            details = {
                "conversation_id": conv_id,
                "composite_score": rot,
                "status": data["status_label"],
                "status_badge": data["status_badge"],
                "recommendation": data["recommendation"],
                "bloat_ratio": f"{bloat}%",
                "dilution_ratio": f"{m['dilution']['score']}%",
                "lost_in_middle": f"{m['lost_in_middle']['score']}%",
                "cognitive_drift": f"{m['drift']['score']}%",
                "transcript_size_mb": m["bloat"]["file_size_mb"],
                "total_steps": m["bloat"]["total_steps"],
                "tool_calls": m["bloat"]["tool_calls"],
                "effective_focus_pct": m["dilution"]["attention_retention_est"],
                "governance_compliance_pct": m["drift"]["governance_compliance_pct"],
                "analyzed_at": datetime.now().isoformat()
            }
            status_tag_clean = data["status_label"].split(" / ")[0].replace("🟢 ", "").replace("🟡 ", "").replace("🟠 ", "").replace("🔴 ", "").strip()
            cur.execute("""
                INSERT INTO "RackTelemetryHistory" 
                (rack_number, rack_name, metric_category, score_value, secondary_value, status_tag, recorded_by, session_id, details_json, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW());
            """, (
                1,
                "Cognitive Health & Memory Rot Meter",
                "MEMORY_ROT",
                rot,
                bloat,
                status_tag_clean,
                "George (Systems Architect)",
                f"ROT-{conv_id[:8]}",
                Json(details)
            ))
            conn.commit()
            return {"status": "success", "data": details}
    finally:
        conn.close()


def main():
    conv_dir = ""
    save_to_db = "--no-save" not in sys.argv
    clean_args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if clean_args:
        arg = clean_args[0]
        if os.path.isdir(arg):
            conv_dir = arg
        else:
            conv_dir = os.path.expanduser(f"~/.gemini/antigravity-cli/brain/{arg}")
    else:
        conv_dir = find_latest_transcript_dir()

    if not conv_dir or not os.path.exists(conv_dir):
        print("❌ Error: Could not locate active conversation directory.")
        sys.exit(1)

    conv_id = os.path.basename(conv_dir)
    transcript_p = os.path.join(conv_dir, ".system_generated", "logs", "transcript.jsonl")

    res = analyze_transcript(transcript_p)
    print_dashboard(res, conv_id)

    if save_to_db:
        db_res = record_memory_rot_to_db()
        if db_res.get("status") == "success":
            print(f"✓ Recorded live empirical Rack 1 snapshot to PostgreSQL RackTelemetryHistory (Score: {res['rot_index']}%)")
        else:
            print(f"⚠️ Note: Database recording skipped ({db_res.get('message')})")


if __name__ == "__main__":
    main()

