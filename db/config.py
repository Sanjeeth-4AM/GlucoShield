"""
GlucoShield Database Configuration
==================================
Environment-variable based database configuration with PostgreSQL production support
and clean SQLite local development / testing fallback.
"""

import os
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Database URL from environment or local development fallback
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "glucoshield.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")

# Standardize postgres:// to postgresql:// for SQLAlchemy 2.0
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Connection pool settings
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
