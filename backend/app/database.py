from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Moteur async
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",  # log SQL en dev
    pool_pre_ping=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Classe de base pour tous les modèles
class Base(DeclarativeBase):
    pass

# Dépendance FastAPI — injectée dans les routes
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# Crée toutes les tables au démarrage
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)