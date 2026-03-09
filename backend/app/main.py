from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config import settings
from app.database import create_tables
from app.routers import jobs, applications
import app.models

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield

app = FastAPI(title="Job Agent API", version="1.0.0", lifespan=lifespan)

app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])

@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}