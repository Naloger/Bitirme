# setup_database.py
import sys

from Libs.Config.config import PAGE_DATABASE_PATH, LEMMA_DATABASE_PATH
from backend.database.init_db import init_db
from backend.database.orm_schema_lemmas import LEMMAS_METADATA
from backend.database.orm_schema_pages import PAGES_METADATA


def main() -> None:
    try:
        init_db(db_path=PAGE_DATABASE_PATH, metadata=PAGES_METADATA)
        print("Database schema initialized successfully.")
    except Exception as exc:
        print(f"Initialization failed: {exc}", file=sys.stderr)
        sys.exit(1)
    try:
        init_db(db_path=LEMMA_DATABASE_PATH, metadata=LEMMAS_METADATA)
        print("Database schema initialized successfully.")
    except Exception as exc:
        print(f"Initialization failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
