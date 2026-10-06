"""
SigmaFidelity™ User Domain Model
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Silas Sync (VP of CRM)
"""

import json
from flask_login import UserMixin

class User(UserMixin):
    """Institutional User Session Model."""

    DEFAULT_ROLE_PERMISSIONS = {
        'Executive': {'*': True},
        'Admin': {'*': True},
        'Manager': {'leads': True, 'accounts': True, 'sales_desk': True, 'bids': True, 'workforce': True, 'monitor': True, 'qms': True},
        'Operator': {'leads': True, 'accounts': True, 'bids': True, 'workforce': True, 'monitor': True, 'qms': True},
        'Sales': {'leads': True, 'accounts': True, 'sales_desk': True, 'bids': True},
        'Estimator': {'bids': True},
        'Technician': {'monitor': True, 'qms': True},
        'Custom': {}
    }

    def __init__(self, id, username, role, full_name=None, custom_permissions=None, email=None):
        self.id = id
        self.username = username
        self.role = role
        self.full_name = full_name
        self.email = email
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

        # Custom role is strictly zero-trust: only explicit granted permissions apply
        if self.role == 'Custom':
            if self.custom_permissions and module in self.custom_permissions:
                perm = self.custom_permissions[module]
                if isinstance(perm, dict):
                    return bool(perm.get(action, False))
                elif isinstance(perm, (list, tuple, set)):
                    return action in perm
                elif isinstance(perm, bool):
                    return perm
            return False

        if self.custom_permissions:
            if module in self.custom_permissions:
                perm = self.custom_permissions[module]
                if isinstance(perm, dict):
                    return bool(perm.get(action, False))
                elif isinstance(perm, (list, tuple, set)):
                    return action in perm
                elif isinstance(perm, bool):
                    return perm
            return False

        # Fallback to role defaults if custom_permissions was never assigned
        role_defaults = self.DEFAULT_ROLE_PERMISSIONS.get(self.role, {})
        if role_defaults.get('*') or role_defaults.get(module):
            return True
        return False

    def has_telegram_permission(self, action: str) -> bool:
        """Evaluates whether the user has granular permission for Telegram operations."""
        if self.role in ['Executive', 'Admin']:
            return True
        if self.custom_permissions and 'telegram' in self.custom_permissions:
            tg = self.custom_permissions['telegram']
            if isinstance(tg, dict):
                if tg.get('enabled') is False:
                    return False
                return bool(tg.get(action, False))
        return False

    def __repr__(self):
        return f"<User id={self.id} username='{self.username}' role='{self.role}'>"

