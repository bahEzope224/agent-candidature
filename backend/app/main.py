from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import create_tables
from app.routers import jobs, applications, auth
import app.models

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield

app = FastAPI(title="Job Agent API", version="1.0.0", lifespan=lifespan)

# CORS — autorise le frontend à appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://job-agent-ibrahima.netlify.app"],  # remplace "*" par ton URL frontend en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])

@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}