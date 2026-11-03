"""
GlucoShield Database Session Management
=======================================
SQLAlchemy 2.0 engine and session factory with connection pooling and dependency generator.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from db.config import DATABASE_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_TIMEOUT, DB_ECHO

connect_args = {}
engine_kwargs = {"echo": DB_ECHO}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = 15.0  # 15-second busy timeout for SQLite file locks
    engine_kwargs["connect_args"] = connect_args
else:
    connect_args["connect_timeout"] = 5  # 5-second socket connect timeout for PostgreSQL
    engine_kwargs["connect_args"] = connect_args
    engine_kwargs["pool_size"] = DB_POOL_SIZE
    engine_kwargs["max_overflow"] = DB_MAX_OVERFLOW
    engine_kwargs["pool_timeout"] = DB_POOL_TIMEOUT

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a SQLAlchemy session per request with clean rollback/close.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
