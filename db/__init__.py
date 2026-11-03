"""
GlucoShield Database Package Initialization
============================================
"""

from db.config import DATABASE_URL
from db.base import Base, TimestampMixin, generate_uuid
from db.session import engine, SessionLocal, get_db
from db.models import (
    User,
    PatientProfile,
    CGMReading,
    InsulinRecord,
    MealRecord,
    FoodAnalysisRecord,
    ForecastRecord,
    WhatIfRecord,
    DecisionRecord,
    WearableObservation
)

__all__ = [
    "DATABASE_URL",
    "Base",
    "TimestampMixin",
    "generate_uuid",
    "engine",
    "SessionLocal",
    "get_db",
    "User",
    "PatientProfile",
    "CGMReading",
    "InsulinRecord",
    "MealRecord",
    "FoodAnalysisRecord",
    "ForecastRecord",
    "WhatIfRecord",
    "DecisionRecord",
    "WearableObservation"
]
