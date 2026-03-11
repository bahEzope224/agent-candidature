from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, field_validator
import structlog

from app.database import get_db
from app.models.user import User
from app.models.profile import Profile
from app.services.auth_service import (
    hash_password, authenticate_user,
    create_access_token, create_refresh_token,
    decode_token, validate_password_strength, get_user_by_email,
)
from app.dependencies import get_current_user
from app.services.email_service import get_gmail_service

logger = structlog.get_logger()
router = APIRouter()


# ── Schémas ────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def strong_password(cls, v):
        ok, msg = validate_password_strength(v)
        if not ok:
            raise ValueError(msg)
        return v

    @field_validator("full_name")
    @classmethod
    def valid_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError("Nom trop court")
        return v.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v):
        ok, msg = validate_password_strength(v)
        if not ok:
            raise ValueError(msg)
        return v


# ── Endpoints ──────────────────────────────────────────────

@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Inscription — crée un compte et un profil vide"""
    existing = await get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    user = User(
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    profile = Profile(
        user_id=user.id,
        first_name=body.full_name.split()[0] if body.full_name else "",
        last_name=" ".join(body.full_name.split()[1:]) if len(body.full_name.split()) > 1 else "",
        skills_technical=[],
        skills_soft=[],
        languages=[],
        tools=[],
        target_roles=["Data Analyst", "Data Scientist"],
        target_locations=["Paris", "Île-de-France"],
        target_contract="stage",
    )
    db.add(profile)
    await db.commit()

    logger.info("Nouvel utilisateur", email=user.email)

    return {
        "access_token": create_access_token(str(user.id), user.email),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
        "user": {"id": str(user.id), "email": user.email, "full_name": user.full_name},
    }


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Connexion avec protection anti-brute force"""
    user, error = await authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail=error)

    return {
        "access_token": create_access_token(str(user.id), user.email),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
        "user": {"id": str(user.id), "email": user.email, "full_name": user.full_name},
    }


@router.post("/refresh")
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Renouvelle l'access token via le refresh token"""
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token invalide")

    from app.services.auth_service import get_user_by_id
    user = await get_user_by_id(db, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")

    return {
        "access_token": create_access_token(str(user.id), user.email),
        "token_type": "bearer",
    }


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    """Retourne l'utilisateur connecté"""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "last_login_at": str(current_user.last_login_at),
    }


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.auth_service import verify_password
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    current_user.hashed_password = hash_password(body.new_password)
    await db.commit()
    return {"message": "Mot de passe modifié"}


@router.get("/gmail/status")
async def gmail_status(current_user: User = Depends(get_current_user)):
    """Statut de la connexion Gmail"""
    try:
        service = get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()
        return {
            "connected": True,
            "email": profile.get("emailAddress"),
            "messages_total": profile.get("messagesTotal"),
        }
    except Exception:
        return {"connected": False}