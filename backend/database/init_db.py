from pathlib import Path
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine
import os
import sys

ENGINE = None
SessionLocal = None


def init_db(db_path, metadata, echo: bool = False):
    """Initialize the database engine, session factory, and create tables."""
    global ENGINE, SessionLocal

    # Normalize pathlib.Path to string and ensure SQLite scheme
    if isinstance(db_path, Path):
        resolved_path = db_path
    elif isinstance(db_path, str) and db_path.startswith("sqlite:///"):
        resolved_path = Path(db_path.replace("sqlite:///", "", 1))
    elif isinstance(db_path, str) and db_path.startswith("sqlite://"):
        # Handle sqlite:// (single slash) or other variants
        resolved_path = Path(db_path.replace("sqlite://", "", 1))
    else:
        # Assume raw path string
        resolved_path = Path(db_path)

    # Resolve to absolute path and ensure parent directory exists
    resolved_path = resolved_path.resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    # Construct final connection string with forward slashes for SQLite compatibility
    connection_url = f"sqlite:///{resolved_path.as_posix()}"

    try:
        ENGINE = create_engine(connection_url, echo=echo)
        SessionLocal = sessionmaker(
            bind=ENGINE, class_=Session, autoflush=False, autocommit=False
        )
        metadata.create_all(bind=ENGINE)
        print(f"Database initialized successfully at: {resolved_path}", file=sys.stdout)
        return ENGINE, SessionLocal
    except Exception as exc:
        print(f"Database initialization failed: {exc}", file=sys.stderr)
        # Additional diagnostic output
        print(f"Resolved DB path: {resolved_path}", file=sys.stderr)
        print(f"Parent directory exists: {resolved_path.parent.exists()}", file=sys.stderr)
        print(
            f"Parent directory writable: {os.access(resolved_path.parent, os.W_OK)}",
            file=sys.stderr,
        )
        raise

