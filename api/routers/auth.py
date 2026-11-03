"""
GlucoShield Authentication & User Management Router
===================================================
Endpoints for user registration, secure login, and profile introspection.
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import User, PatientProfile
from api.schemas import UserRegister, UserLogin, UserResponse, TokenResponse
from api.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from api.deps import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & User Management"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Registers a new user with secure password hashing and automatically provisions
    a default clinical patient profile. Returns a signed JWT access token.
    """
    # 1. Check for duplicate email
    existing = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # 2. Hash password and persist user
    hashed = get_password_hash(payload.password)
    user = User(
        email=payload.email.lower().strip(),
        hashed_password=hashed,
        full_name=payload.full_name,
        is_active=True,
        is_superuser=False
    )
    db.add(user)
    db.flush()

    # 3. Create default patient profile for the user
    default_patient = PatientProfile(
        user_id=user.id,
        patient_display_id=f"PATIENT-{user.id[:8].upper()}",
        age=45.0,
        bmi=26.5,
        diabetes_duration_years=10.0,
        hba1c=58.0,
        glycated_albumin=18.0,
        fasting_glucose=130.0,
        fasting_c_peptide=0.8,
        macrovascular_comp_count=0.0,
        microvascular_comp_count=0.0,
        is_t1dm=1.0
    )
    db.add(default_patient)
    db.commit()
    db.refresh(user)

    # 4. Generate JWT
    token = create_access_token(data={"sub": user.id, "email": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )

@router.post("/login", response_model=TokenResponse)
def login_user(
    payload: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticates email and password credentials. Returns a signed JWT access token.
    """
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated."
        )

    token = create_access_token(data={"sub": user.id, "email": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves the currently authenticated user's profile metadata.
    """
    return UserResponse.model_validate(current_user)
