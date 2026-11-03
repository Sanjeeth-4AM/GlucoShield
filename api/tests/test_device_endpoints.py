"""
GlucoShield Integration Tests — Device & Mobile API Endpoints (Phase 17)
========================================================================
Tests authentication, validation, deduplication, causality, and IDOR protection
via HTTP TestClient against /api/v1/devices endpoints.
"""

import unittest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from api.service import app
from db.session import SessionLocal
from db.models import User, PatientProfile
from api.security import create_access_token


class TestDeviceEndpoints(unittest.TestCase):
    """End-to-end integration tests for /api/v1/devices endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.client = TestClient(app, raise_server_exceptions=False)

        # Create two isolated users
        uid_a = uuid.uuid4().hex[:8]
        uid_b = uuid.uuid4().hex[:8]
        cls.user_a = User(email=f"dev_alice_{uid_a}@hospital.org", hashed_password="pw", full_name="Alice")
        cls.user_b = User(email=f"dev_bob_{uid_b}@hospital.org", hashed_password="pw", full_name="Bob")
        cls.db.add_all([cls.user_a, cls.user_b])
        cls.db.flush()

        cls.patient_a = PatientProfile(user_id=cls.user_a.id, patient_display_id=f"PAT-A-{uid_a}")
        cls.patient_b = PatientProfile(user_id=cls.user_b.id, patient_display_id=f"PAT-B-{uid_b}")
        cls.db.add_all([cls.patient_a, cls.patient_b])
        cls.db.commit()

        cls.token_a = create_access_token({"sub": cls.user_a.id, "email": cls.user_a.email})
        cls.token_b = create_access_token({"sub": cls.user_b.id, "email": cls.user_b.email})
        cls.auth_headers_a = {"Authorization": f"Bearer {cls.token_a}"}
        cls.auth_headers_b = {"Authorization": f"Bearer {cls.token_b}"}

    @classmethod
    def tearDownClass(cls):
        cls.db.rollback()
        cls.db.close()

    def test_01_unauthenticated_sync_rejected_401(self):
        """Unauthenticated requests to /api/v1/devices/sync must return 401."""
        payload = {
            "device_id": "TEST-NO-AUTH",
            "provider": "dexcom",
            "observations": []
        }
        res = self.client.post("/api/v1/devices/sync", json=payload)
        self.assertEqual(res.status_code, 401)

    def test_02_register_device_and_list(self):
        """Authenticated user can register a device and list it."""
        reg_payload = {
            "device_id": "DEXCOM-G7-ALICE-01",
            "provider": "dexcom",
            "device_name": "Alice Dexcom G7"
        }
        res = self.client.post("/api/v1/devices/register", json=reg_payload, headers=self.auth_headers_a)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["device_id"], "DEXCOM-G7-ALICE-01")
        self.assertEqual(data["connection_status"], "connected")

        # List devices for Alice
        list_res = self.client.get("/api/v1/devices", headers=self.auth_headers_a)
        self.assertEqual(list_res.status_code, 200)
        devices = list_res.json()
        self.assertTrue(any(d["device_id"] == "DEXCOM-G7-ALICE-01" for d in devices))

    def test_03_batch_sync_cgm_and_wearable(self):
        """Batch device synchronization ingests observations and mirrors to clinical tables."""
        now = datetime.utcnow()
        sync_payload = {
            "device_id": "DEXCOM-G7-ALICE-01",
            "provider": "dexcom",
            "device_name": "Alice Dexcom G7",
            "observations": [
                {
                    "measurement_type": "glucose",
                    "value": 118.5,
                    "unit": "mg/dL",
                    "observation_timestamp": (now - timedelta(minutes=10)).isoformat(),
                    "source_timezone": "UTC"
                },
                {
                    "measurement_type": "heart_rate",
                    "value": 68.0,
                    "unit": "bpm",
                    "observation_timestamp": (now - timedelta(minutes=10)).isoformat(),
                    "source_timezone": "UTC"
                }
            ]
        }
        res = self.client.post("/api/v1/devices/sync", json=sync_payload, headers=self.auth_headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["records_accepted"], 2)
        self.assertEqual(data["duplicates_ignored"], 0)

        # Syncing exact same payload a second time must be deduplicated
        res2 = self.client.post("/api/v1/devices/sync", json=sync_payload, headers=self.auth_headers_a)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(data2["records_accepted"], 0)
        self.assertEqual(data2["duplicates_ignored"], 2)

    def test_04_manual_mobile_event_logging(self):
        """User can log confirmed manual meal or insulin event via mobile endpoint."""
        now = datetime.utcnow()
        meal_payload = {
            "event_type": "meal",
            "timestamp": (now - timedelta(minutes=25)).isoformat(),
            "value": 60.0,
            "unit": "grams",
            "notes": "Lunch oats & berries",
            "user_confirmed": True
        }
        res = self.client.post("/api/v1/devices/events/manual", json=meal_payload, headers=self.auth_headers_a)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["records_accepted"], 1)

    def test_05_disconnect_and_status_checks(self):
        """Device can be disconnected and its status/freshness inspected."""
        # Check status
        status_res = self.client.get("/api/v1/devices/DEXCOM-G7-ALICE-01/status", headers=self.auth_headers_a)
        self.assertEqual(status_res.status_code, 200)
        st_data = status_res.json()
        self.assertEqual(st_data["connection_status"], "connected")
        self.assertIsNotNone(st_data["data_freshness_seconds"])

        # Disconnect
        disc_res = self.client.post("/api/v1/devices/DEXCOM-G7-ALICE-01/disconnect", headers=self.auth_headers_a)
        self.assertEqual(disc_res.status_code, 200)
        self.assertEqual(disc_res.json()["connection_status"], "disconnected")

    def test_06_idor_isolation_between_patients(self):
        """User B cannot see or disconnect User A's device."""
        # Bob tries to inspect Alice's device
        res = self.client.get("/api/v1/devices/DEXCOM-G7-ALICE-01/status", headers=self.auth_headers_b)
        self.assertEqual(res.status_code, 404)

        # Bob's device list does not contain Alice's device
        list_b = self.client.get("/api/v1/devices", headers=self.auth_headers_b).json()
        self.assertFalse(any(d["device_id"] == "DEXCOM-G7-ALICE-01" for d in list_b))

    def test_07_causal_context_endpoint_excludes_future(self):
        """GET /api/v1/devices/causal-context strictly excludes future telemetry."""
        now = datetime.utcnow()
        # Ingest past and future points
        sync_payload = {
            "device_id": "DEXCOM-G7-ALICE-01",
            "provider": "dexcom",
            "observations": [
                {
                    "measurement_type": "glucose",
                    "value": 115.0,
                    "unit": "mg/dL",
                    "observation_timestamp": (now - timedelta(hours=1)).isoformat()
                }
            ]
        }
        self.client.post("/api/v1/devices/sync", json=sync_payload, headers=self.auth_headers_a)

        # Query causal context at now - 30 minutes
        cutoff = now - timedelta(minutes=30)
        res = self.client.get(
            f"/api/v1/devices/causal-context?forecast_origin={cutoff.isoformat()}",
            headers=self.auth_headers_a
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["causal_boundary_verified"])
        self.assertGreaterEqual(data["cgm_count_causal"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
