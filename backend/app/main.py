from fastapi import FastAPI, Request
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

# CORS — autorise le frontend à appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://job-agent-ibrahima.netlify.app", 
        "https://agent-candidature.vercel.app",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


# ── Capturer les erreurs 500 non gérées ───────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    await write_log(
        level="FATAL",
        action="UNHANDLED_EXCEPTION",
        details={
            "url": str(request.url),
            "method": request.method,
            "error": str(exc),
            "traceback": tb[-2000:],  # Limiter à 2000 caractères
        },
    )
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur"})


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}