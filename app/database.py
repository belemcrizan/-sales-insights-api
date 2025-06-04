from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
import os

# Environment variables or default values
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./sales.db")
ECHO_SQL = os.getenv("ECHO_SQL", "True").lower() in ("true", "1", "t")

# Engine configuration
engine = create_async_engine(
    DATABASE_URL,
    echo=ECHO_SQL,  # Better to control via environment variable
    poolclass=NullPool,  # Recommended for SQLite to avoid connection issues
    future=True,  # Use SQLAlchemy 2.0 behavior
    connect_args={"check_same_thread": False}  # SQLite specific
)

# Session factory with proper async_sessionmaker
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Useful for async operations
    autoflush=False
)

# Base for models
Base = declarative_base()

# Dependency for FastAPI or other frameworks
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async generator that yields database sessions."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()