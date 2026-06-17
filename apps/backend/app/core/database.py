from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import create_engine

from app.core.config import settings


class Base(DeclarativeBase):
    pass


# Async engine (FastAPI) — optimized pool settings for production
async_engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=30,          # Wait up to 30s for a connection
    pool_recycle=1800,        # Recycle connections every 30 min
    pool_pre_ping=True,       # Verify connection before use
    echo=settings.app_env == "development",
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Synchronous engine (Celery tasks)
_sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
sync_engine = create_engine(
    _sync_url,
    pool_size=5,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=False,
)

SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)