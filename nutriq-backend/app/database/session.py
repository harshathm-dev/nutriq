import os
import uuid
from typing import AsyncGenerator
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# For sqlite vs postgresql handling
is_sqlite = "sqlite" in settings.DATABASE_URL.lower()

# Normalize SQLite database path to absolute path to guarantee stability across working directory reloads
db_url = settings.DATABASE_URL
if is_sqlite:
    # If URL contains relative path, make it absolute relative to backend root
    if "sqlite+aiosqlite:///" in db_url and not db_url.startswith("sqlite+aiosqlite:////"):
        rel_path = db_url.replace("sqlite+aiosqlite:///", "")
        if rel_path.startswith("./") or rel_path.startswith(".\\"):
            rel_path = rel_path[2:]
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        abs_db_path = os.path.abspath(os.path.join(backend_dir, rel_path))
        # Ensure directory exists
        os.makedirs(os.path.dirname(abs_db_path), exist_ok=True)
        # Format as SQLite URL (4 slashes on Windows for drive letter or absolute path)
        norm_path = abs_db_path.replace("\\", "/")
        db_url = f"sqlite+aiosqlite:///{norm_path}"

engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "check_same_thread": False,
        "timeout": 30
    } if is_sqlite else {}
)

# Apply SQLite performance, concurrency, and reliability PRAGMAs
if is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Request-scoped database session dependency.
    Creates a new AsyncSession per request, yields it to the API handler,
    rolls back in case of an unhandled exception, and guarantees session closure.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

