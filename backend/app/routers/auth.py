"""
Router Auth — Inscription / Connexion / Profil
------------------------------------------------
POST /api/auth/register  → créer un compte
POST /api/auth/login     → obtenir un token JWT
GET  /api/auth/me        → profil de l'utilisateur connecté
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
import structlog


from app.database import get_db
from app.models.user import User
from app.models.profile import Profile
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter()
logger = structlog.get_logger()


# ================================================================
# SCHÉMAS PYDANTIC
# ================================================================

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str | None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# ================================================================
# ROUTES
# ================================================================

@router.post("/register", status_code=201)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Crée un nouveau compte utilisateur"""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte existe déjà avec cet email",
        )

    user = User(
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        is_active=True,
    )
    db.add(user)
    await db.flush()

    profile = Profile(user_id=user.id)
    db.add(profile)
    await db.commit()

    token = create_access_token(user.id, user.email)
    logger.info("Nouvel utilisateur créé", email=user.email)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
    }


@router.post("/login")
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Accepte JSON {"email": "...", "password": "..."}
    OU form-data (OAuth2 compatible)
    """
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        body = await request.json()
        email = body.get("email")
        password = body.get("password")
    else:
        form = await request.form()
        email = form.get("username") or form.get("email")
        password = form.get("password")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email et mot de passe requis",
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )

    token = create_access_token(user.id, user.email)
    logger.info("Connexion réussie", email=user.email)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Retourne le profil de l'utilisateur connecté"""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "created_at": str(current_user.created_at),
    }


# ================================================================
# ROUTES GMAIL — conservées, inchangées
# ================================================================

@router.get("/gmail/connect")
async def gmail_connect():
    try:
        from app.services.email_service import get_gmail_service
        service = get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()
        return {"status": "already_connected", "email": profile.get("emailAddress")}
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "action": "Lance 'python scripts/auth_gmail.py' dans ton terminal",
        }


@router.get("/gmail/status")
async def gmail_status():
    from pathlib import Path
    from app.config import settings

    token_file = Path(settings.GMAIL_TOKEN_FILE)
    if not token_file.exists():
        return {"connected": False, "message": "Token Gmail absent"}

    try:
        from app.services.email_service import get_gmail_service
        service = get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()
        return {
            "connected": True,
            "email": profile.get("emailAddress"),
            "messages_total": profile.get("messagesTotal"),
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}
