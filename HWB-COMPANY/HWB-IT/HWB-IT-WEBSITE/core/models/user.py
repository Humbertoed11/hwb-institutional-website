"""
SigmaFidelity™ User Domain Model
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Silas Sync (VP of CRM)
"""

import json
from flask_login import UserMixin

class User(UserMixin):
    """Institutional User Session Model."""
    def __init__(self, id, username, role, full_name=None, custom_permissions=None):
        self.id = id
        self.username = username
        self.role = role
        self.full_name = full_name
        self.custom_permissions = custom_permissions or {}
        if isinstance(self.custom_permissions, str):
            try:
                self.custom_permissions = json.loads(self.custom_permissions)
            except Exception:
                self.custom_permissions = {}

    def has_permission(self, module: str, action: str = 'view') -> bool:
        """Evaluates whether the user has granular permission for a system module."""
        if self.role in ['Executive', 'Admin']:
            return True
        if self.custom_permissions and module in self.custom_permissions:
            return bool(self.custom_permissions[module].get(action, False))
        return False

    def __repr__(self):
        return f"<User id={self.id} username='{self.username}' role='{self.role}'>"
