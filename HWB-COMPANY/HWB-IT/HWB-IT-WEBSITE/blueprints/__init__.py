"""
SigmaFidelity™ Enterprise Modular Blueprint Hub
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Silas Sync (VP of CRM)
"""

from flask import Flask, Blueprint
from .telemetry import telemetry_bp
from .bids import bids_bp
from .auth import auth_bp
from .public import public_bp
from .operations import operations_bp
from .crm_api import crm_api_bp
from .academy import academy_bp

def register_blueprint_hub(app: Flask, bp: Blueprint, **kwargs) -> None:
    """
    Registers a Blueprint on the Flask app and maps root endpoint aliases
    to ensure 100% backward compatibility with existing url_for() calls in templates.
    """
    app.register_blueprint(bp, **kwargs)
    for rule in list(app.url_map.iter_rules()):
        if rule.endpoint.startswith(f"{bp.name}."):
            short_name = rule.endpoint.split('.', 1)[1]
            if short_name not in app.view_functions:
                try:
                    app.add_url_rule(rule.rule, endpoint=short_name, view_func=app.view_functions[rule.endpoint], methods=rule.methods)
                except Exception:
                    pass

__all__ = [
    "telemetry_bp",
    "bids_bp",
    "auth_bp",
    "public_bp",
    "operations_bp",
    "crm_api_bp",
    "academy_bp",
    "register_blueprint_hub"
]
