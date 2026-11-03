"""
GlucoShield — Hardened Environment & Configuration Management (Phase 16)
========================================================================
Implements strict configuration profiles (DEVELOPMENT, TEST, VALIDATION, PRODUCTION)
with fail-safe security validations preventing dev defaults from leaking into production.
"""

import os
import sys
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass, field

class EnvironmentProfile(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    TEST = "TEST"
    VALIDATION = "VALIDATION"
    PRODUCTION = "PRODUCTION"

INSECURE_DEV_SECRET = "glucoshield_clinical_super_secret_jwt_key_phase10_2026"

@dataclass
class AppConfig:
    """Production-hardened application configuration."""
    app_env: EnvironmentProfile = field(default_factory=lambda: EnvironmentProfile(os.getenv("APP_ENV", "DEVELOPMENT").upper()))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    
    # Security & Auth
    jwt_secret_key: str = field(default_factory=lambda: os.getenv("JWT_SECRET_KEY", INSECURE_DEV_SECRET))
    jwt_algorithm: str = field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    access_token_expire_minutes: int = field(default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")))
    
    # Database
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./glucoshield.db"))
    db_pool_size: int = field(default_factory=lambda: int(os.getenv("DB_POOL_SIZE", "10")))
    db_max_overflow: int = field(default_factory=lambda: int(os.getenv("DB_MAX_OVERFLOW", "20")))
    db_pool_timeout: int = field(default_factory=lambda: int(os.getenv("DB_POOL_TIMEOUT", "30")))
    db_echo: bool = field(default_factory=lambda: os.getenv("DB_ECHO", "false").lower() == "true")

    # CORS
    cors_origins: List[str] = field(default_factory=lambda: [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()])

    # Model & Inference Governance
    active_model_version: str = field(default_factory=lambda: os.getenv("ACTIVE_MODEL_VERSION", "V1_FROZEN").upper())
    dev_mode_active: bool = field(default_factory=lambda: os.getenv("GLUCOSHIELD_DEV_MODE", "false").lower() == "true")
    
    # Rate Limiting & Resource Protection
    rate_limit_enabled: bool = field(default_factory=lambda: os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true")
    rate_limit_general_rpm: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_GENERAL_RPM", "120")))
    rate_limit_inference_rpm: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_INFERENCE_RPM", "30")))
    max_request_size_bytes: int = field(default_factory=lambda: int(os.getenv("MAX_REQUEST_SIZE_BYTES", "10485760"))) # 10MB

    # Concurrency
    max_concurrent_inferences: int = field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_INFERENCES", "4")))

    def __post_init__(self):
        self.validate_environment_safety()

    def validate_environment_safety(self):
        """Enforces hard security invariants for PRODUCTION profile."""
        if self.app_env == EnvironmentProfile.PRODUCTION:
            # 1. Debug mode must NOT be active
            if self.debug:
                raise ValueError("SECURITY VIOLATION: DEBUG mode cannot be active when APP_ENV=PRODUCTION.")

            # 2. Insecure default secret must NOT be used
            if self.jwt_secret_key == INSECURE_DEV_SECRET or len(self.jwt_secret_key) < 32:
                raise ValueError(
                    "SECURITY VIOLATION: Default or low-entropy JWT_SECRET_KEY cannot be used in PRODUCTION. "
                    "Set a 256-bit random secret via environment variable."
                )

            # 3. Dev mode must NOT be active
            if self.dev_mode_active:
                raise ValueError("GOVERNANCE VIOLATION: GLUCOSHIELD_DEV_MODE cannot be active in PRODUCTION.")

            # 4. CORS wildcard warning
            if "*" in self.cors_origins:
                print("[WARNING] Wildcard CORS (*) detected in PRODUCTION configuration. Restrict to authorized client domains.")

def get_config() -> AppConfig:
    """Returns singleton validated configuration."""
    return AppConfig()
