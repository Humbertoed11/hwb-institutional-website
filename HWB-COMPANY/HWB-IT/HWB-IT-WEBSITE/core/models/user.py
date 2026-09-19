"""
SigmaFidelity™ User Domain Model
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Silas Sync (VP of CRM)
"""

from flask_login import UserMixin

class User(UserMixin):
    """Institutional User Session Model."""
    def __init__(self, id, username, role, full_name=None):
        self.id = id
        self.username = username
        self.role = role
        self.full_name = full_name

    def __repr__(self):
        return f"<User id={self.id} username='{self.username}' role='{self.role}'>"
