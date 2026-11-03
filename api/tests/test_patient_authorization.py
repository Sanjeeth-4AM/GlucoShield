"""
GlucoShield Unit Tests — Patient Authorization & Horizontal IDOR Isolation
==========================================================================
Tests ensuring strict data isolation: User A cannot read or mutate User B's patient data.
"""

import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.base import Base
from db.models import User, PatientProfile
from db.session import get_db
from api.service import app
from api.security import create_access_token, get_password_hash

class TestPatientAuthorization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(cls.test_engine)
        cls.TestSessionLocal = sessionmaker(
            bind=cls.test_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )

        def override_get_db():
            db = cls.TestSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

        # Provision two separate users and one superuser
        db = cls.TestSessionLocal()
        cls.user_a = User(
            email="user_a@clinic.org",
            hashed_password=get_password_hash("PassA123!"),
            is_active=True,
            is_superuser=False
        )
        cls.user_b = User(
            email="user_b@clinic.org",
            hashed_password=get_password_hash("PassB123!"),
            is_active=True,
            is_superuser=False
        )
        cls.superuser = User(
            email="admin@clinic.org",
            hashed_password=get_password_hash("AdminPass123!"),
            is_active=True,
            is_superuser=True
        )
        db.add_all([cls.user_a, cls.user_b, cls.superuser])
        db.flush()

        cls.patient_a = PatientProfile(
            user_id=cls.user_a.id,
            patient_display_id="PATIENT-A",
            age=48.0,
            hba1c=56.0
        )
        cls.patient_b = PatientProfile(
            user_id=cls.user_b.id,
            patient_display_id="PATIENT-B",
            age=60.0,
            hba1c=68.0
        )
        db.add_all([cls.patient_a, cls.patient_b])
        db.commit()

        cls.patient_a_id = cls.patient_a.id
        cls.patient_b_id = cls.patient_b.id
        cls.token_a = create_access_token({"sub": cls.user_a.id, "email": cls.user_a.email})
        cls.token_b = create_access_token({"sub": cls.user_b.id, "email": cls.user_b.email})
        cls.token_admin = create_access_token({"sub": cls.superuser.id, "email": cls.superuser.email})
        db.close()

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def test_user_can_access_own_patient_data(self):
        res = self.client.get(
            f"/api/v1/patients/{self.patient_a_id}",
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["patient_display_id"], "PATIENT-A")

    def test_user_cannot_access_other_users_patient_profile(self):
        # User B attempts to access User A's patient profile -> Must return 403 Forbidden
        res = self.client.get(
            f"/api/v1/patients/{self.patient_a_id}",
            headers={"Authorization": f"Bearer {self.token_b}"}
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("not authorized", res.json()["detail"].lower())

    def test_user_cannot_mutate_other_users_patient(self):
        # User B attempts to update User A's patient -> Must return 403 Forbidden
        res = self.client.put(
            f"/api/v1/patients/{self.patient_a_id}",
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={"age": 99.0}
        )
        self.assertEqual(res.status_code, 403)

    def test_user_cannot_post_cgm_to_other_users_patient(self):
        # User B attempts to push CGM readings to Patient A -> Must return 403 Forbidden
        res = self.client.post(
            f"/api/v1/patients/{self.patient_a_id}/cgm",
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={"readings": [{"timestamp": "2026-08-30T12:00:00", "cgm_glucose": 150.0}]}
        )
        self.assertEqual(res.status_code, 403)

    def test_user_cannot_read_other_users_cgm_history(self):
        # User B attempts to read Patient A's CGM history -> Must return 403 Forbidden
        res = self.client.get(
            f"/api/v1/patients/{self.patient_a_id}/cgm",
            headers={"Authorization": f"Bearer {self.token_b}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_superuser_can_access_any_patient(self):
        # Admin can access Patient A and Patient B
        res_a = self.client.get(
            f"/api/v1/patients/{self.patient_a_id}",
            headers={"Authorization": f"Bearer {self.token_admin}"}
        )
        self.assertEqual(res_a.status_code, 200)

        res_b = self.client.get(
            f"/api/v1/patients/{self.patient_b_id}",
            headers={"Authorization": f"Bearer {self.token_admin}"}
        )
        self.assertEqual(res_b.status_code, 200)

if __name__ == "__main__":
    unittest.main()
