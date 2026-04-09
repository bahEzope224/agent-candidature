from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.config import settings
from app.database import create_tables, AsyncSessionLocal
from app.routers import jobs, applications, auth, profile
import app.models
from app.routers import admin
from app.models.system_log import SystemLog
from datetime import datetime, timedelta
import uuid
import traceback
from app.services.auth_service import decode_token

# ── Helper: écrire un log + purger les +30j ───────────────────
async def write_log(level: str, action: str, details: dict, user_id=None):
    try:
        async with AsyncSessionLocal() as db:
            # Purge des logs plus vieux que 30 jours
            cutoff = datetime.utcnow() - timedelta(days=30)
            from sqlalchemy import delete as sql_delete
            await db.execute(sql_delete(SystemLog).where(SystemLog.created_at < cutoff))
            # Insertion du nouveau log
            log = SystemLog(
                id=uuid.uuid4(),
                user_id=user_id,
                level=level,
                action=action,
                details=details,
            )
            db.add(log)
            await db.commit()
    except Exception:
        pass  # Ne jamais planter à cause des logs

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield

app = FastAPI(title="Job Agent API", version="1.0.0", lifespan=lifespan)

# CORS — autorise le frontend et l'extension Chrome (dynamique) à appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://job-agent-ibrahima.netlify.app", 
        "https://agent-candidature.vercel.app",
        "http://localhost:5173"
    ],
    allow_origin_regex="chrome-extension://.*",  # Autorise toutes les extensions chrome
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


# ── Helper: payload renvoyé au client pour toute erreur ───────
def _build_error_payload(request: Request, exc: Exception, *, error_id: str, friendly_message: str = None) -> dict:
    raw_message = getattr(exc, "detail", None) or str(exc) or "Erreur inattendue"
    user_message = friendly_message
    if not user_message:
        if isinstance(raw_message, str) and raw_message.strip():
            user_message = raw_message
        else:
            user_message = f"Une erreur est survenue. Merci de réessayer dans quelques instants (réf {error_id})."
    if isinstance(user_message, str) and f"réf {error_id}" not in user_message:
        user_message = f"{user_message} (réf {error_id})"
    return {
        "error_id": error_id,
        "error": str(raw_message),
        "detail": user_message,
        "location": {
            "method": request.method,
            "path": request.url.path,
        },
    }


def _extract_user_id(request: Request):
    auth = request.headers.get("authorization", "")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except HTTPException:
        return None


# ── Capturer les HTTPException pour renvoyer l'erreur au client ──
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    error_id = str(uuid.uuid4())
    user_id = _extract_user_id(request)
    await write_log(
        level="ERROR",
        action="HTTP_EXCEPTION",
        details={
            "error_id": error_id,
            "url": str(request.url),
            "method": request.method,
            "status_code": exc.status_code,
            "error": str(exc.detail),
        },
        user_id=user_id,
    )
    payload = _build_error_payload(request, exc, error_id=error_id)
    return JSONResponse(status_code=exc.status_code, content=payload)


# ── Capturer les erreurs 500 non gérées ───────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid.uuid4())
    user_id = _extract_user_id(request)
    tb = traceback.format_exc()
    await write_log(
        level="FATAL",
        action="UNHANDLED_EXCEPTION",
        details={
            "error_id": error_id,
            "url": str(request.url),
            "method": request.method,
            "error": str(exc),
            "traceback": tb[-2000:],  # Limiter à 2000 caractères
        },
        user_id=user_id,
    )
    payload = _build_error_payload(
        request,
        exc,
        error_id=error_id,
        friendly_message=f"Une erreur est survenue côté serveur. Merci de réessayer dans quelques instants (réf {error_id}).",
    )
    return JSONResponse(status_code=500, content=payload)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
