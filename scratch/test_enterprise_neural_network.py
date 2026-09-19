#!/usr/bin/env python3
"""
Test Suite: Enterprise Neural Network & Cognitive Architecture (Phase 1-3)
Standard: HWB-QMS-11.3 / Fortune 500 Cognitive Parity / ISO 9001 Clause 7.1.6
Author: Systems Architect George
"""

import sys
import os
import unittest
import time
import requests
from dotenv import load_dotenv

sys.path.insert(0, '/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE')
load_dotenv('/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/.env')

from core.services.embedding import get_embedding, get_embeddings_batch, calculate_hash_embedding
from main_app import app

class TestEnterpriseNeuralNetwork(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_01_embedding_dimension_and_caching(self):
        """Verify 1536-dimensional semantic embedding and in-memory cache acceleration."""
        test_text = "Commercial office janitorial and daily custodial services"
        t0 = time.time()
        v1 = get_embedding(test_text)
        t1 = time.time()
        self.assertEqual(len(v1), 1536)
        self.assertIsInstance(v1[0], float)

        # Second call must hit in-memory cache (near zero latency)
        t2 = time.time()
        v2 = get_embedding(test_text)
        t3 = time.time()
        self.assertEqual(v1, v2)
        self.assertLess(t3 - t2, 0.01)

    def test_02_batch_embedding_engine(self):
        """Verify batch embedding generation across multiple concepts."""
        texts = [
            "VCT floor stripping and waxing protocol",
            "Medical terminal cleaning and biohazard disinfection",
            "Post-construction rough and final cleaning takeoff"
        ]
        results = get_embeddings_batch(texts)
        self.assertEqual(len(results), 3)
        for vec in results:
            self.assertEqual(len(vec), 1536)

    def test_03_deterministic_fallback(self):
        """Verify deterministic mathematical hash fallback projection."""
        fallback = calculate_hash_embedding("Fallback resilience test")
        self.assertEqual(len(fallback), 1536)
        self.assertTrue(all(-1.0 <= val <= 1.0 for val in fallback))

    def test_04_hybrid_kb_search_endpoint(self):
        """Verify /api/v1/kb/search returns hybrid RRF results with 1536d semantic matching."""
        res = self.client.get('/api/v1/kb/search?q=database+migration')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'SUCCESS')
        self.assertGreater(data['results_count'], 0)
        self.assertIn('rrf_score', data['results'][0])

    def test_05_preflight_risk_audit_endpoint(self):
        """Verify /api/v1/kb/preflight returns structured risk profile and mandatory guardrails."""
        res = self.client.get('/api/v1/kb/preflight?q=phone+number+standardization')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn(data['status'], ['GUARDRAILS_MANDATED', 'AUDIT_CLEARED'])
        self.assertIn('risk_level', data)
        self.assertIn('scars', data)
        self.assertIn('mandatory_guardrails', data)
        self.assertGreater(data['relevant_scars_count'], 0)

    def test_06_preflight_cli_utility(self):
        """Verify scripts/preflight_audit.py executes cleanly without runtime exception."""
        import subprocess
        venv_python = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/.venv/bin/python3"
        cmd = [venv_python, "scripts/preflight_audit.py", "testing preflight CLI"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("AUDIT VERDICT", proc.stdout)

if __name__ == '__main__':
    unittest.main()
