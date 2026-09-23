"""SQLAlchemy engine / session setup.

Uses SQLite by default for zero-config local development, but the models are
written to be MySQL-compatible (see DATABASE_URL in .env).
"""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

def _normalize_db_url(url: str) -> str:
    """Make common Postgres URLs work with our installed driver (psycopg 3).

    Managed providers (Neon, etc.) hand out `postgres://` or `postgresql://`
    URLs, but SQLAlchemy maps those to psycopg2 by default. We install psycopg 3,
    so route them to the `postgresql+psycopg` dialect automatically.
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = _normalize_db_url(settings.database_url)

connect_args = {}
engine_kwargs = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    # Needed so SQLite works with FastAPI's threaded request handling.
    connect_args = {"check_same_thread": False}
else:
    # Recycle connections so serverless DBs (Neon scale-to-zero) don't hand us
    # stale sockets after an idle period.
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# New nullable columns added after the initial release. `create_all` never
# ALTERs existing tables, so ensure_schema() adds any missing ones on both the
# hosted Postgres DB and local SQLite without dropping data. (Alembic is the
# longer-term answer as the schema keeps evolving.)
_ADDED_COLUMNS = {
    "wardrobe_items": [
        ("display_image_url", "VARCHAR(700)"),
        ("image_public_id", "VARCHAR(300)"),
        ("attributes", "JSON"),
    ],
}


def ensure_schema() -> None:
    """Idempotently add missing nullable columns to pre-existing tables."""
    insp = inspect(engine)
    for table, columns in _ADDED_COLUMNS.items():
        if not insp.has_table(table):
            continue  # fresh DB: create_all already built it with all columns
        existing = {c["name"] for c in insp.get_columns(table)}
        missing = [(name, ddl) for name, ddl in columns if name not in existing]
        if not missing:
            continue
        with engine.begin() as conn:
            for name, ddl in missing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def init_db() -> None:
    """Create all tables and apply lightweight column migrations."""
    from app import models  # noqa: F401  (ensures models are imported)

    Base.metadata.create_all(bind=engine)
    ensure_schema()
