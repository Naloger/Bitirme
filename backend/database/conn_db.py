import sqlite3
from Libs.Config.config import PAGE_DATABASE_PATH

def get_db_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(str(PAGE_DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn
