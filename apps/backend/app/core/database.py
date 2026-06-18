from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import create_engine

from app.core.config import settings


class Base(DeclarativeBase):
    pass


# Ensure the URL uses the async driver for create_async_engine.
# Render (and many providers) supply "postgresql://..." — we need "+asyncpg".
_async_url = settings.database_url
if "+asyncpg" not in _async_url:
    _async_url = _async_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Async engine (FastAPI) — optimized pool settings for production
async_engine = create_async_engine(
    _async_url,
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


# Synchronous engine (Celery tasks) — always needs psycopg2 sync driver
_sync_url = _async_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
sync_engine = create_engine(
    _sync_url,
    pool_size=5,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=False,
)

SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)