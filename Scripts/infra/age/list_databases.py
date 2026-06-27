# -*- coding: utf-8 -*-
"""Script to list available user databases in the PostgreSQL container."""

import sys
from pathlib import Path

# Add project root to python path if needed
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import psycopg2
from Scripts.infra.age.age_helpers import PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, DEFAULT_DB


def main():
    print(f"🔌 Connecting to PostgreSQL at {PG_HOST}:{PG_PORT}...")
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=DEFAULT_DB,
            user=PG_USER,
            password=PG_PASSWORD
        )
        with conn.cursor() as cursor:
            # Query standard pg_database to list user-facing databases
            cursor.execute("""
                SELECT d.datname, pg_catalog.pg_get_userbyid(d.datdba) as owner,
                       pg_catalog.pg_encoding_to_char(d.encoding) as encoding
                FROM pg_catalog.pg_database d
                WHERE d.datistemplate = false
                ORDER BY d.datname;
            """)
            
            print("\n📋 Available PostgreSQL/AGE Databases:")
            print("-" * 60)
            print(f"{'Database Name':<25} | {'Owner':<15} | {'Encoding'}")
            print("-" * 60)
            for record in cursor.fetchall():
                name, owner, encoding = record
                print(f"{name:<25} | {owner:<15} | {encoding}")
            print("-" * 60)
        conn.close()
    except Exception as e:
        print(f"\n❌ Error listing databases: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
