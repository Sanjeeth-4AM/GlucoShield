"""
GlucoShield Unit Tests — Authentication & JWT Security
======================================================
Tests for password hashing, registration, duplicate email rejection, JWT issuance,
and protected endpoint authentication.
"""

import unittest
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.base import Base
from db.models import User
from db.session import get_db
from api.service import app
from api.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token
)

class TestAuthenticationSecurity(unittest.TestCase):
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
            autoflush=False
        )

        def override_get_db():
            db = cls.TestSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def test_bcrypt_hashing_and_verification(self):
        raw_pw = "ClinicalSecurePass2026!"
        hashed = get_password_hash(raw_pw)
        
        self.assertNotEqual(raw_pw, hashed)
        self.assertTrue(verify_password(raw_pw, hashed))
        self.assertFalse(verify_password("WrongPassword123", hashed))

    def test_jwt_issuance_and_expiration(self):
        payload = {"sub": "user-uuid-123", "email": "test@glucoshield.ai"}
        token = create_access_token(payload, expires_delta=timedelta(minutes=5))
        
        decoded = decode_access_token(token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["sub"], "user-uuid-123")
        self.assertEqual(decoded["email"], "test@glucoshield.ai")

        # Test expired token
        expired_token = create_access_token(payload, expires_delta=timedelta(seconds=-10))
        expired_decoded = decode_access_token(expired_token)
        self.assertIsNone(expired_decoded)

    def test_user_registration_and_login_flow(self):
        email = "doctor_john@hospital.org"
        pw = "SuperDoctorPassword2026!"
        
        # 1. Register
        reg_res = self.client.post("/api/v1/auth/register", json={
            "email": email,
            "password": pw,
            "full_name": "Dr. John Watson"
        })
        self.assertEqual(reg_res.status_code, 201)
        reg_data = reg_res.json()
        self.assertIn("access_token", reg_data)
        self.assertEqual(reg_data["user"]["email"], email)
        self.assertEqual(reg_data["user"]["full_name"], "Dr. John Watson")

        # 2. Duplicate Registration Rejection
        dup_res = self.client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "AnotherPassword123"
        })
        self.assertEqual(dup_res.status_code, 400)
        self.assertIn("already exists", dup_res.json()["detail"])

        # 3. Successful Login
        login_res = self.client.post("/api/v1/auth/login", json={
            "email": email,
            "password": pw
        })
        self.assertEqual(login_res.status_code, 200)
        login_data = login_res.json()
        self.assertIn("access_token", login_data)
        token = login_data["access_token"]

        # 4. Invalid Password Login
        bad_pw_res = self.client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "WrongPassword999!"
        })
        self.assertEqual(bad_pw_res.status_code, 401)

        # 5. Access Protected /auth/me
        me_res = self.client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()["email"], email)

        # 6. Reject Missing or Malformed Token
        unauth_res = self.client.get("/api/v1/auth/me")
        self.assertEqual(unauth_res.status_code, 401)

        bad_token_res = self.client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid_gibberish_token_string"
        })
        self.assertEqual(bad_token_res.status_code, 401)

if __name__ == "__main__":
    unittest.main()
