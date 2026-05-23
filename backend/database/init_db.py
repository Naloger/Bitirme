from pathlib import Path
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session, create_engine
import os
import sys

# from backend.database.orm_schema import  StructuredPageModel, UnstructuredPageModel, WikiPageModel
from Libs.Config.config import DATABASE_PATH
from backend.database import orm_schema  # noqa: F401

ENGINE = None
SessionLocal = None


def init_db(url: str = DATABASE_PATH, echo: bool = False):
    """Initialize the database engine, session factory, and create tables."""
    global ENGINE, SessionLocal

    # Normalize pathlib.Path to string and ensure SQLite scheme
    if isinstance(url, Path):
        db_path = url
    elif url.startswith("sqlite:///"):
        db_path = Path(url.replace("sqlite:///", "", 1))
    elif url.startswith("sqlite://"):
        # Handle sqlite:// (single slash) or other variants
        db_path = Path(url.replace("sqlite://", "", 1))
    else:
        # Assume raw path string
        db_path = Path(url)

    # Resolve to absolute path and ensure parent directory exists
    db_path = db_path.resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Construct final connection string with forward slashes for SQLite compatibility
    connection_url = f"sqlite:///{db_path.as_posix()}"

    try:
        ENGINE = create_engine(connection_url, echo=echo)
        SessionLocal = sessionmaker(
            bind=ENGINE, class_=Session, autoflush=False, autocommit=False
        )
        SQLModel.metadata.create_all(bind=ENGINE)
        print(f"Database initialized successfully at: {db_path}", file=sys.stdout)
        return ENGINE, SessionLocal
    except Exception as exc:
        print(f"Database initialization failed: {exc}", file=sys.stderr)
        # Additional diagnostic output
        print(f"Resolved DB path: {db_path}", file=sys.stderr)
        print(f"Parent directory exists: {db_path.parent.exists()}", file=sys.stderr)
        print(
            f"Parent directory writable: {os.access(db_path.parent, os.W_OK)}",
            file=sys.stderr,
        )
        raise
