"""
SigmaFidelity™ User Domain Model
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Silas Sync (VP of CRM)
"""

import json
from flask_login import UserMixin

ROLE_MODULE_PRESETS = {
    'Executive': {
        'leads': {'view': True, 'edit': True, 'delete': True},
        'accounts': {'view': True, 'edit': True, 'delete': True},
        'sales_desk': {'view': True, 'edit': True, 'delete': True},
        'bids': {'view': True, 'edit': True, 'delete': True},
        'workforce': {'view': True, 'edit': True, 'delete': True},
        'monitor': {'view': True, 'edit': True, 'delete': True},
        'qms': {'view': True, 'edit': True, 'delete': True},
        'social': {'view': True, 'edit': True, 'delete': True},
        'outbox': {'view': True, 'edit': True, 'delete': True},
        'users': {'view': True, 'edit': True, 'delete': True},
        'tools': {'view': True, 'edit': True, 'delete': True}
    },
    'Admin': {
        'leads': {'view': True, 'edit': True, 'delete': True},
        'accounts': {'view': True, 'edit': True, 'delete': True},
        'sales_desk': {'view': True, 'edit': True, 'delete': True},
        'bids': {'view': True, 'edit': True, 'delete': True},
        'workforce': {'view': True, 'edit': True, 'delete': True},
        'monitor': {'view': True, 'edit': True, 'delete': True},
        'qms': {'view': True, 'edit': True, 'delete': True},
        'social': {'view': True, 'edit': True, 'delete': True},
        'outbox': {'view': True, 'edit': True, 'delete': True},
        'users': {'view': True, 'edit': True, 'delete': True},
        'tools': {'view': True, 'edit': True, 'delete': True}
    },
    'Manager': {
        'leads': {'view': True, 'edit': True, 'delete': False},
        'accounts': {'view': True, 'edit': True, 'delete': False},
        'sales_desk': {'view': True, 'edit': True, 'delete': False},
        'bids': {'view': True, 'edit': True, 'delete': False},
        'workforce': {'view': True, 'edit': True, 'delete': False},
        'monitor': {'view': True, 'edit': True, 'delete': False},
        'qms': {'view': True, 'edit': True, 'delete': False},
        'social': {'view': True, 'edit': False, 'delete': False},
        'outbox': {'view': True, 'edit': False, 'delete': False},
        'users': {'view': True, 'edit': False, 'delete': False},
        'tools': {'view': True, 'edit': False, 'delete': False}
    },
    'Operator': {
        'leads': {'view': True, 'edit': True, 'delete': False},
        'accounts': {'view': True, 'edit': False, 'delete': False},
        'sales_desk': {'view': False, 'edit': False, 'delete': False},
        'bids': {'view': True, 'edit': False, 'delete': False},
        'workforce': {'view': True, 'edit': True, 'delete': False},
        'monitor': {'view': True, 'edit': True, 'delete': False},
        'qms': {'view': True, 'edit': False, 'delete': False},
        'social': {'view': False, 'edit': False, 'delete': False},
        'outbox': {'view': False, 'edit': False, 'delete': False},
        'users': {'view': False, 'edit': False, 'delete': False},
        'tools': {'view': False, 'edit': False, 'delete': False}
    },
    'Sales': {
        'leads': {'view': True, 'edit': True, 'delete': False},
        'accounts': {'view': True, 'edit': True, 'delete': False},
        'sales_desk': {'view': True, 'edit': True, 'delete': False},
        'bids': {'view': True, 'edit': False, 'delete': False},
        'workforce': {'view': False, 'edit': False, 'delete': False},
        'monitor': {'view': False, 'edit': False, 'delete': False},
        'qms': {'view': True, 'edit': False, 'delete': False},
        'social': {'view': False, 'edit': False, 'delete': False},
        'outbox': {'view': False, 'edit': False, 'delete': False},
        'users': {'view': False, 'edit': False, 'delete': False},
        'tools': {'view': False, 'edit': False, 'delete': False}
    },
    'Estimator': {
        'leads': {'view': False, 'edit': False, 'delete': False},
        'accounts': {'view': False, 'edit': False, 'delete': False},
        'sales_desk': {'view': False, 'edit': False, 'delete': False},
        'bids': {'view': True, 'edit': True, 'delete': False},
        'workforce': {'view': False, 'edit': False, 'delete': False},
        'monitor': {'view': False, 'edit': False, 'delete': False},
        'qms': {'view': True, 'edit': False, 'delete': False},
        'social': {'view': False, 'edit': False, 'delete': False},
        'outbox': {'view': False, 'edit': False, 'delete': False},
        'users': {'view': False, 'edit': False, 'delete': False},
        'tools': {'view': False, 'edit': False, 'delete': False}
    },
    'Technician': {
        'leads': {'view': False, 'edit': False, 'delete': False},
        'accounts': {'view': False, 'edit': False, 'delete': False},
        'sales_desk': {'view': False, 'edit': False, 'delete': False},
        'bids': {'view': False, 'edit': False, 'delete': False},
        'workforce': {'view': False, 'edit': False, 'delete': False},
        'monitor': {'view': True, 'edit': True, 'delete': False},
        'qms': {'view': True, 'edit': False, 'delete': False},
        'social': {'view': False, 'edit': False, 'delete': False},
        'outbox': {'view': False, 'edit': False, 'delete': False},
        'users': {'view': False, 'edit': False, 'delete': False},
        'tools': {'view': False, 'edit': False, 'delete': False}
    },
    'Custom': {
        'leads': {'view': False, 'edit': False, 'delete': False},
        'accounts': {'view': False, 'edit': False, 'delete': False},
        'sales_desk': {'view': False, 'edit': False, 'delete': False},
        'bids': {'view': False, 'edit': False, 'delete': False},
        'workforce': {'view': False, 'edit': False, 'delete': False},
        'monitor': {'view': False, 'edit': False, 'delete': False},
        'qms': {'view': False, 'edit': False, 'delete': False},
        'social': {'view': False, 'edit': False, 'delete': False},
        'outbox': {'view': False, 'edit': False, 'delete': False},
        'users': {'view': False, 'edit': False, 'delete': False},
        'tools': {'view': False, 'edit': False, 'delete': False}
    }
}

class User(UserMixin):
    """Institutional User Session Model."""

    ROLE_MODULE_PRESETS = ROLE_MODULE_PRESETS
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

        if self.custom_permissions and module in self.custom_permissions:
            perm = self.custom_permissions[module]
            if isinstance(perm, dict):
                return bool(perm.get(action, False))
            elif isinstance(perm, (list, tuple, set)):
                return action in perm
            elif isinstance(perm, bool):
                return perm
            return False

        # Fallback to role defaults if custom_permissions was never assigned or module is not overridden
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

