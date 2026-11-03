"""
GlucoShield Database Base & Model Mixins
========================================
DeclarativeBase definition and reusable mixins for UUID keys and timestamp auditing.
"""

import uuid
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, String

class Base(DeclarativeBase):
    """SQLAlchemy 2.0 Declarative Base."""
    pass

class TimestampMixin:
    """Provides created_at and updated_at datetime columns."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

def generate_uuid() -> str:
    """Generates a UUID4 string for primary keys."""
    return str(uuid.uuid4())
