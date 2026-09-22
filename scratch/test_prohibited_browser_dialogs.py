#!/usr/bin/env python3
"""
Test Suite: Zero-Tolerance Prohibited Browser Dialogs (Poka-Yoke Quality Gate)
Standard: HWB-QMS-7.2 / SigmaFidelity™ Industrial Form & UI Standards (2026)
Author: George (Systems Architect & Senior ISO 9001 Auditor)

Enforces:
1. Complete elimination of raw browser dialogs: window.alert(), window.confirm(), window.prompt().
2. Institutional modal architecture: modal-decision and showDecision() in backoffice_base.html.
3. User governance delete actions must use styled decision modals with audit logging.
"""

import os
import re
import unittest

TEMPLATES_DIR = '/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/templates'
STATIC_DIR = '/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static'

# Files excluded from scan: snapshots, legacy retired mocks, or external third-party libs
EXCLUDED_SUBDIRS = ['.snapshots', 'vendor', 'libs', 'legacy']
EXCLUDED_FILES = ['HWB-MOB-App.html', 'HWB-WEB Csi.html', 'tma_estimator.html']  # Prototype UI mocks / Telegram WebApps

class TestProhibitedBrowserDialogs(unittest.TestCase):

    def _get_files_to_scan(self):
        target_files = []
        for root, dirs, files in os.walk(TEMPLATES_DIR):
            if any(ex in root for ex in EXCLUDED_SUBDIRS):
                continue
            for f in files:
                if f.endswith('.html') and f not in EXCLUDED_FILES:
                    target_files.append(os.path.join(root, f))
        for root, dirs, files in os.walk(STATIC_DIR):
            if any(ex in root for ex in EXCLUDED_SUBDIRS):
                continue
            for f in files:
                if f.endswith('.js'):
                    target_files.append(os.path.join(root, f))
        return target_files

    def test_01_no_raw_confirm_in_active_templates(self):
        """Verify 0 instances of window.confirm() or inline confirm() across active backoffice templates."""
        pattern = re.compile(r'(?<!showDecision\()\bconfirm\s*\(', re.IGNORECASE)
        violations = []
        for path in self._get_files_to_scan():
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_no, line in enumerate(f, 1):
                    # Ignore comments
                    stripped = line.strip()
                    if stripped.startswith('//') or stripped.startswith('<!--') or stripped.startswith('*'):
                        continue
                    if pattern.search(line):
                        violations.append(f"{os.path.basename(path)}:{line_no} -> {stripped}")
        
        self.assertEqual(len(violations), 0, f"Found prohibited confirm() calls:\n" + "\n".join(violations))

    def test_02_no_raw_alert_in_active_templates(self):
        """Verify 0 instances of window.alert() or inline alert() across active backoffice templates."""
        pattern = re.compile(r'\balert\s*\(', re.IGNORECASE)
        violations = []
        for path in self._get_files_to_scan():
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_no, line in enumerate(f, 1):
                    stripped = line.strip()
                    if stripped.startswith('//') or stripped.startswith('<!--') or stripped.startswith('*') or stripped.startswith('/*') or '/*' in stripped:
                        continue
                    # Ignore python/jinja or CSS alerts like alert-danger
                    if 'class="alert' in line or 'class=\'alert' in line or 'send_teams_alert' in line:
                        continue
                    if pattern.search(line):
                        violations.append(f"{os.path.basename(path)}:{line_no} -> {stripped}")
        
        self.assertEqual(len(violations), 0, f"Found prohibited alert() calls:\n" + "\n".join(violations))

    def test_03_no_raw_prompt_in_active_templates(self):
        """Verify 0 instances of window.prompt() across active templates."""
        pattern = re.compile(r'\bprompt\s*\(', re.IGNORECASE)
        violations = []
        for path in self._get_files_to_scan():
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_no, line in enumerate(f, 1):
                    stripped = line.strip()
                    if stripped.startswith('//') or stripped.startswith('<!--') or stripped.startswith('*'):
                        continue
                    if pattern.search(line):
                        violations.append(f"{os.path.basename(path)}:{line_no} -> {stripped}")
        
        self.assertEqual(len(violations), 0, f"Found prohibited prompt() calls:\n" + "\n".join(violations))

    def test_04_global_decision_modal_architecture(self):
        """Verify backoffice_base.html defines modal-decision and showDecision()."""
        base_path = os.path.join(TEMPLATES_DIR, 'backoffice_base.html')
        with open(base_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('id="modal-decision"', content, "backoffice_base.html must contain modal-decision")
        self.assertIn('function showDecision(', content, "backoffice_base.html must define showDecision()")
        self.assertIn('function showToast(', content, "backoffice_base.html must define showToast()")

    def test_05_user_governance_delete_action_uses_modal(self):
        """Verify HWB-WEB Sigma Executive.html uses confirmDeleteUser and does NOT use raw confirm."""
        exec_path = os.path.join(TEMPLATES_DIR, 'HWB-WEB Sigma Executive.html')
        with open(exec_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('confirmDeleteUser', content, "Sigma Executive must implement confirmDeleteUser()")
        self.assertNotIn("onsubmit=\"return confirm(", content, "Sigma Executive must not use raw onsubmit=confirm()")

if __name__ == '__main__':
    unittest.main()
