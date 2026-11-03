"""
GlucoShield API Dependencies & Authorization Guards
===================================================
JWT extraction, user validation, and patient ownership authorization checks.
"""

from typing import Optional, Generator
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import User, PatientProfile
from api.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Validates JWT access token from Authorization header and retrieves active user.
    Raises 401 Unauthorized if missing, invalid, or expired.
    """
    raw_token = token
    if not raw_token and authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            raw_token = parts[1]

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_access_token(raw_token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload["sub"]
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated."
        )

    return user

def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Extracts user if valid token is provided, returns None otherwise (does not raise 401).
    Allows optional persistence on scientific inference endpoints.
    """
    raw_token = token
    if not raw_token and authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            raw_token = parts[1]

    if not raw_token:
        return None

    payload = decode_access_token(raw_token)
    if not payload or "sub" not in payload:
        return None

    user_id = payload["sub"]
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    return user

def verify_patient_ownership(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> PatientProfile:
    """
    Verifies that the requested patient profile exists and belongs to the authenticated user.
    Prevents horizontal privilege escalation (IDOR). Superusers bypass ownership checks.
    """
    patient = db.query(PatientProfile).filter(PatientProfile.id == patient_id).first()
    if not patient:
        # Also check by patient_display_id if UUID didn't match directly
        patient = db.query(PatientProfile).filter(
            PatientProfile.patient_display_id == patient_id,
            PatientProfile.user_id == current_user.id
        ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient profile '{patient_id}' not found."
        )

    if not current_user.is_superuser and patient.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access or modify this patient's clinical data."
        )

    return patient
