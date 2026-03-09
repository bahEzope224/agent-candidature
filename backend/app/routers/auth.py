from fastapi import APIRouter
from fastapi.responses import RedirectResponse
import structlog

router = APIRouter()
logger = structlog.get_logger()


@router.get("/gmail/connect")
async def gmail_connect():
    """Lance le flux OAuth2 Gmail dans le navigateur"""
    try:
        from app.services.email_service import get_gmail_service
        service = get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()
        return {
            "status": "already_connected",
            "email": profile.get("emailAddress"),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "action": "Lance 'python scripts/auth_gmail.py' dans ton terminal",
        }


@router.get("/gmail/status")
async def gmail_status():
    """Vérifie si Gmail est connecté"""
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