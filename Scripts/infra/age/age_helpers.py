# -*- coding: utf-8 -*-
"""Shared Apache AGE connection and graph management utility functions."""

import json
import sys
import uuid
from typing import List, Any
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure stdout to use UTF-8 to support Windows console output
if sys.stdout.encoding != 'utf-8':
    reconfigure_stdout = getattr(sys.stdout, 'reconfigure', None)
    if reconfigure_stdout:
        try:
            reconfigure_stdout(encoding='utf-8')
        except Exception:
            pass

# Apache AGE Database connection details
PG_HOST = "127.0.0.1"
PG_PORT = "5435"
PG_USER = "postgres"
PG_PASSWORD = "local_rag_secret_key_123"
DEFAULT_DB = "postgres"  # Bootstrap database connection


def ensure_database_exists(db_name: str) -> None:
    """Ensure that a PostgreSQL database exists and initialize the Apache AGE extension in it."""
    # 1. Connect to the default database (postgres) to create target database if needed
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        database=DEFAULT_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT datname FROM pg_database;")
            existing_dbs = [row[0] for row in cur.fetchall()]
            if db_name not in existing_dbs:
                print(f"[INFO] Database '{db_name}' does not exist. Creating...")
                # Safe formatting for database names (quoted identifier)
                cur.execute(f'CREATE DATABASE "{db_name}";')
                print(f"[SUCCESS] Database '{db_name}' created.")
            else:
                print(f"[INFO] Database '{db_name}' already exists.")
    finally:
        conn.close()

    # 2. Connect to the target database and initialize AGE extension
    target_conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        database=db_name,
        user=PG_USER,
        password=PG_PASSWORD
    )
    target_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    try:
        with target_conn.cursor() as cur:
            print(f"[INFO] Initializing Apache AGE extension in database '{db_name}'...")
            cur.execute("CREATE EXTENSION IF NOT EXISTS age;")
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, '$user', public;")
            print(f"[SUCCESS] Apache AGE extension initialized in '{db_name}'.")
    finally:
        target_conn.close()


def get_age_connection(db_name: str) -> psycopg2.extensions.connection:
    """Get an active connection to the database with Apache AGE loaded and path configured."""
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        database=db_name,
        user=PG_USER,
        password=PG_PASSWORD
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, '$user', public;")
    return conn


def create_age_graph(conn: psycopg2.extensions.connection, graph_name: str) -> None:
    """Create an Apache AGE graph."""
    with conn.cursor() as cur:
        try:
            cur.execute(f"SELECT create_graph('{graph_name}');")
            print(f"[SUCCESS] Apache AGE graph '{graph_name}' created.")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"[INFO] Apache AGE graph '{graph_name}' already exists.")
            else:
                raise


def drop_age_graph(conn: psycopg2.extensions.connection, graph_name: str) -> None:
    """Drop an Apache AGE graph and cascade deletion of all tables."""
    with conn.cursor() as cur:
        try:
            # Terminate other connections to release table locks
            cur.execute("""
                SELECT pg_terminate_backend(pid) 
                FROM pg_stat_activity 
                WHERE datname = current_database() 
                  AND pid <> pg_backend_pid();
            """)
            cur.execute(f"SELECT drop_graph('{graph_name}', true);")
            print(f"[SUCCESS] Apache AGE graph '{graph_name}' dropped.")
        except Exception as e:
            print(f"[INFO] Failed to drop graph '{graph_name}': {e}")



def parse_agtype(val: Any) -> Any:
    """Parse an agtype response value from Apache AGE into Python types."""
    if val is None:
        return None
    val_str = str(val)
    if "::" in val_str:
        val_str = val_str.split("::")[0]
    
    try:
        return json.loads(val_str)
    except Exception:
        if val_str.startswith('"') and val_str.endswith('"'):
            return val_str[1:-1]
        return val_str


def execute_cypher_param(
    cur: psycopg2.extensions.cursor,
    graph_name: str,
    cypher_query: str,
    params_dict: dict,
    col_defs: str = "as (a agtype)"
) -> List[tuple]:
    """
    Execute a parameterized Cypher query using on-the-fly PostgreSQL prepared statements.
    This bypasses the Apache AGE requirement that the third argument to the cypher() function
    must be a Postgres parameter placeholder.
    """
    stmt_name = f"stmt_{uuid.uuid4().hex}"
    prepare_sql = f"PREPARE {stmt_name}(agtype) AS SELECT * FROM cypher('{graph_name}', $${cypher_query}$$, $1) {col_defs};"
    
    cur.execute(prepare_sql)
    try:
        cur.execute(f"EXECUTE {stmt_name}(%s);", (json.dumps(params_dict),))
        try:
            return cur.fetchall()
        except psycopg2.ProgrammingError:
            # Query did not return any rows
            return []
    finally:
        cur.execute(f"DEALLOCATE {stmt_name};")
