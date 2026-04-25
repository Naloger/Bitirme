import sqlite3
import os


def create_database(folder_path, db_name, schema):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    db_path = os.path.join(folder_path, db_name)

    try:
        # The 'with' block handles opening and closing automatically
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.executescript(schema)
            # No need for conn.commit() inside 'with' for schema scripts
            print(f"Successfully created database at: {db_path}")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")


# --- Configuration ---
TARGET_FOLDER = "../db"
DATABASE_NAME = "graph.db"

# Define your schema here
SQL_SCHEMA = """


-- 1. The core entities (People, items, etc.)
CREATE TABLE IF NOT EXISTS nodes (
    node_id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_name TEXT UNIQUE NOT NULL
);

-- 2. Transaction nodes (The 'containers' for inputs)
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Directed, weighted relationships
-- X to Y and Y to X are distinct rows here
CREATE TABLE IF NOT EXISTS relationships (
    source_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    weight REAL DEFAULT 1.0,
    PRIMARY KEY (source_id, target_id),
    FOREIGN KEY (source_id) REFERENCES nodes(node_id),
    FOREIGN KEY (target_id) REFERENCES nodes(node_id)
);

-- 4. Linking transactions to nodes
-- This connects your inputs to the transaction node
CREATE TABLE IF NOT EXISTS transaction_links (
    transaction_id INTEGER NOT NULL,
    node_id INTEGER NOT NULL,
    weight REAL DEFAULT 1.0, -- Default weight 1 as requested
    PRIMARY KEY (transaction_id, node_id),
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id),
    FOREIGN KEY (node_id) REFERENCES nodes(node_id)
);


"""

if __name__ == "__main__":
    create_database(TARGET_FOLDER, DATABASE_NAME, SQL_SCHEMA)
