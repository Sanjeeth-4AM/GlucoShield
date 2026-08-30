"""
GlucoShield Phase 9 — Frontend & Static Asset Integration Tests
===============================================================
Verifies that the compiled React dashboard is correctly hosted by FastAPI,
static assets resolve properly, API routes remain unshadowed, and model hashes
are preserved.
"""

import sys
import os
import unittest
import hashlib
from fastapi.testclient import TestClient

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from api.service import app

def sha256_file(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192 * 1024):
            h.update(chunk)
    return h.hexdigest().lower()

class TestFrontendIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def test_01_frontend_dist_files_exist(self):
        """Test 1: Check that frontend/dist contains index.html and assets."""
        dist_dir = os.path.join(BASE_DIR, "frontend", "dist")
        self.assertTrue(os.path.exists(dist_dir), "frontend/dist directory must exist")
        index_html = os.path.join(dist_dir, "index.html")
        self.assertTrue(os.path.exists(index_html), "frontend/dist/index.html must exist")
        assets_dir = os.path.join(dist_dir, "assets")
        self.assertTrue(os.path.exists(assets_dir), "frontend/dist/assets must exist")

    def test_02_root_endpoint_serves_frontend_html(self):
        """Test 2: GET / returns HTTP 200 and serves GlucoShield dashboard HTML."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.headers.get("content-type", ""))
        content = resp.text
        self.assertIn("GLUCOSHIELD", content.upper())
        self.assertIn("root", content)

    def test_03_api_health_not_shadowed_by_static_mount(self):
        """Test 3: Verify /api/v1/health is still reachable and not swallowed by static SPA routing."""
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["active_channels_contract"], 22)

    def test_04_api_food_analyze_not_shadowed(self):
        """Test 4: Verify POST /api/v1/food/analyze remains functional."""
        payload = {
            "food_name_query": "banana",
            "portion_g": 118.0
        }
        resp = self.client.post("/api/v1/food/analyze", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["selected_food"], "banana")
        self.assertTrue(data["requires_user_confirmation"])

    def test_05_frozen_model_hashes_intact(self):
        """Test 5: Verify bitwise frozen model and scaler hashes remain unchanged."""
        neural_h = sha256_file(os.path.join(BASE_DIR, "models", "glucoshield_neural_best.pt"))
        hybrid_h = sha256_file(os.path.join(BASE_DIR, "models", "glucoshield_hybrid_best.pt"))
        feat_h = sha256_file(os.path.join(BASE_DIR, "data", "metadata", "feature_scaler.joblib"))
        stat_h = sha256_file(os.path.join(BASE_DIR, "data", "metadata", "static_scaler.joblib"))

        self.assertEqual(neural_h, "026af3341a91064136c38b0172f2aa6af34806913640a02270c7d82a28ea13fb")
        self.assertEqual(hybrid_h, "89a67710aa4931246f9097674332cbfd9d1af3d20c722c04d806ef66e47298d1")
        self.assertEqual(feat_h, "757f5c99e294dc8c5698a42cee1843853e8506df5203508aa71a1462d545972b")
        self.assertEqual(stat_h, "fedc25f67dbcefd2c19ff38375568f3f2bc83ac1fa7c29840e5c81d33b479576")

if __name__ == "__main__":
    unittest.main(verbosity=2)
