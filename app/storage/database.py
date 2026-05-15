"""SQLite database engine and session helpers."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.storage.models import Base

_engine = None
_SessionLocal = None


def get_database_url() -> str:
    """Return configured database URL."""
    return get_settings().database_url


def get_engine(database_url: str | None = None):
    """Return a cached SQLAlchemy engine."""
    global _engine
    url = database_url or get_database_url()
    if _engine is None or str(_engine.url) != url.replace("sqlite:///", "sqlite:///"):
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args, future=True)
    return _engine


def get_sessionmaker(database_url: str | None = None):
    """Return a cached SQLAlchemy sessionmaker."""
    global _SessionLocal
    engine = get_engine(database_url)
    if _SessionLocal is None or _SessionLocal.kw.get("bind") is not engine:
        _SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
    return _SessionLocal


def get_db_session(database_url: str | None = None) -> Session:
    """Create a database session."""
    return get_sessionmaker(database_url)()


def session_scope(database_url: str | None = None) -> Generator[Session, None, None]:
    """Provide a transactional session scope."""
    session = get_db_session(database_url)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(database_url: str | None = None) -> None:
    """Create all journal tables."""
    Base.metadata.create_all(bind=get_engine(database_url))


def reset_engine_cache() -> None:
    """Reset cached engine/sessionmaker for tests."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
