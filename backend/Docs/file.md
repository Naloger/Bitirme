backend/
    backend/
        ├── api/
        │   ├── api.py          # Endpoints
        │   ├── database.py     # DB connection & SQL queries
        │   ├── schemas.py      # Pydantic models ✅ KEEP HERE
        │   └── __init__.py
        ├── database/           # ← NEW (sibling to api)
        │   ├── __init__.py
        │   ├── schema.sql      # Database schema (CREATE TABLE statements)
        │   ├── init_db.py      # Script to initialize DB from schema.sql
        │   └── migrations/     # Future schema changes
        ├── data/
        │   └── pages.db
        └── pyproject.toml