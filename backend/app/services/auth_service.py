"""
Service d'authentification JWT
--------------------------------
- Hash des mots de passe avec bcrypt (via PyJWT + hashlib)
- Génération et vérification des tokens JWT
- Dépendance FastAPI get_current_user injectable dans toutes les routes
"""

import uuid
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.user import User

# Schéma OAuth2 — pointe vers la route de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 jours


# ================================================================
# HASH MOT DE PASSE (pbkdf2 — pas besoin de bcrypt)
# ================================================================

def hash_password(password: str) -> str:
    """Hash un mot de passe avec PBKDF2-SHA256"""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=260000,
    )
    return f"pbkdf2:sha256:260000:{salt}:{key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Vérifie un mot de passe contre son hash"""
    try:
        _, algo, iterations, salt, stored_key = hashed.split(":")
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=int(iterations),
        )
        return hmac.compare_digest(key.hex(), stored_key)
    except Exception:
        return False


# ================================================================
# JWT
# ================================================================

def create_access_token(user_id: uuid.UUID, email: str) -> str:
    """Génère un JWT signé avec l'id et l'email de l'utilisateur"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Décode et valide un JWT"""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expiré — reconnectez-vous",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ================================================================
# DÉPENDANCE FASTAPI — à injecter dans toutes les routes protégées
# ================================================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dépendance injectable dans n'importe quelle route.
    Retourne l'utilisateur connecté ou lève 401.

    Usage dans une route :
        async def ma_route(current_user: User = Depends(get_current_user)):
    """
    payload = decode_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide — sub manquant",
        )

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable ou désactivé",
        )

    return user
