# setup_database.py
import sys

from backend.database.init_db import init_db


def main() -> None:
    try:
        init_db()
        print("Database schema initialized successfully.")
    except Exception as exc:
        print(f"Initialization failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
