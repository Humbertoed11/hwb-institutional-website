"""
SigmaFidelity™ Enterprise Version & Deployment Sentinel
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Peter (Recovery Specialist)
"""

import os
import json
import subprocess
from typing import Dict, Any

APP_SEMANTIC_VERSION = "v5.4.1"

def _detect_git_commit() -> str:
    """Safely retrieves short git commit hash from repository or environment."""
    commit = os.getenv("GIT_COMMIT") or os.getenv("COMMIT_HASH")
    if commit:
        return commit[:7]
    try:
        cmd = ["git", "rev-parse", "--short", "HEAD"]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=2).decode().strip()
        if output:
            return output
    except Exception:
        pass
    return "ba53a5f"


def _is_running_on_azure() -> bool:
    """Detects whether the application is running inside Microsoft Azure App Service."""
    if os.getenv("WEBSITE_SITE_NAME") or os.getenv("REGION_NAME") or os.getenv("WEBSITE_SKU"):
        return True
    
    # Check version.json override if deployed
    search_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "version.json"),
        "/app/version.json",
        "version.json"
    ]
    for p in search_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("environment") == "AZURE_PRODUCTION":
                        return True
            except Exception:
                pass

    return False


def get_version_info() -> Dict[str, Any]:
    """
    Returns unified version and deployment telemetry.
    Format adheres to Option A: Semantic & Git Hash (e.g. v5.4.1 (ba53a5f)).
    """
    search_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "version.json"),
        "/app/version.json",
        "version.json"
    ]
    file_data = {}
    for p in search_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                    break
            except Exception:
                pass

    app_version = file_data.get("version", APP_SEMANTIC_VERSION)
    commit = file_data.get("commit") or _detect_git_commit()
    build_date = file_data.get("build_date", "2026-10-07")
    build_tag = file_data.get("build_tag", f"{app_version}-{commit}")

    # Determine environment
    env_override = file_data.get("environment")
    is_azure = (env_override == "AZURE_PRODUCTION") or _is_running_on_azure()
    
    env_label = "LIVE AZURE" if is_azure else "LOCAL DEV"
    env_code = "AZURE_PRODUCTION" if is_azure else "LOCAL_DEV"
    
    # Option A: Semantic & Git Hash
    display_version = f"{app_version} ({commit}) · {env_label}"

    return {
        "app_version": app_version,
        "commit": commit,
        "build_date": build_date,
        "build_tag": build_tag,
        "environment": env_code,
        "env_label": env_label,
        "is_azure": is_azure,
        "display_version": display_version
    }
