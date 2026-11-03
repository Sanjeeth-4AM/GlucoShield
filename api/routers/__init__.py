"""
GlucoShield API Routers Package
===============================
"""

from api.routers.auth import router as auth_router
from api.routers.patients import router as patients_router
from api.routers.analytics import router as analytics_router
from api.routers.devices import router as devices_router
from api.routers.cohort import router as cohort_router

__all__ = ["auth_router", "patients_router", "analytics_router", "devices_router", "cohort_router"]
