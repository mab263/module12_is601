"""Database engine, session factory, declarative base, and the request dependency."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/fastapi_db",
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class every SQLAlchemy model inherits from."""


def get_db():
    """FastAPI dependency: give each request its own session and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()