from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.config import settings
import structlog

logger = structlog.get_logger()

# Bcrypt avec coût élevé — résistant au brute force
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Vérifie la robustesse du mot de passe"""
    if len(password) < 8:
        return False, "Minimum 8 caractères"
    if not any(c.isupper() for c in password):
        return False, "Au moins une majuscule requise"
    if not any(c.isdigit() for c in password):
        return False, "Au moins un chiffre requis"
    return True, "OK"


def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    from uuid import UUID
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    return result.scalar_one_or_none()


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> tuple[Optional[User], str]:
    """
    Authentifie un utilisateur.
    Retourne (user, error_message).
    Implémente le verrouillage après N tentatives.
    """
    user = await get_user_by_email(db, email)

    if not user:
        # Temps constant pour éviter l'énumération d'emails
        verify_password("dummy", "$2b$12$dummy.hash.to.prevent.timing.attacks.padding")
        return None, "Email ou mot de passe incorrect"

    if not user.is_active:
        return None, "Compte désactivé"

    # Vérifie le verrouillage
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
        return None, f"Compte verrouillé — réessaie dans {remaining} min"

    # Vérifie le mot de passe
    if not verify_password(password, user.hashed_password):
        attempts = int(user.failed_login_attempts or "0") + 1
        user.failed_login_attempts = str(attempts)

        if attempts >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_login_attempts = "0"
            await db.commit()
            logger.warning("Compte verrouillé", email=email, attempts=attempts)
            return None, f"Trop de tentatives — compte verrouillé {LOCKOUT_MINUTES} min"

        await db.commit()
        return None, f"Email ou mot de passe incorrect ({MAX_LOGIN_ATTEMPTS - attempts} essais restants)"

    # Succès — réinitialise les compteurs
    user.failed_login_attempts = "0"
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    await db.commit()

    logger.info("Connexion réussie", email=email)
    return user, ""