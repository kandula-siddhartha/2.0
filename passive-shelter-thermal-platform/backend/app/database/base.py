"""
SQLAlchemy database engine, session, and base model.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import sys
import os

# Add parent to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import settings

engine = create_engine(
    settings.resolved_database_url,
    connect_args={"check_same_thread": False},  # SQLite specific
    echo=settings.dev_mode,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a database session and ensures cleanup."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for use outside of FastAPI request handlers."""
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
