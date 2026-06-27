import sys
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

PG_HOST = "127.0.0.1"
PG_PORT = "5435"
PG_DB = "postgres"  # Standard default database for bootstrap connection
PG_USER = "postgres"
PG_PASSWORD = "local_rag_secret_key_123"

TARGET_DATABASES = ["keyword_db", "memory_db"]

def main():
    print(f"🔌 Connecting to PostgreSQL at {PG_HOST}:{PG_PORT}...")
    try:
        # 1. Connect to the default database to execute CREATE DATABASE
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with conn.cursor() as cursor:
            # Query all existing databases
            cursor.execute("SELECT datname FROM pg_database;")
            existing_dbs = [row[0] for row in cursor.fetchall()]
            
            for db_name in TARGET_DATABASES:
                print(f"🛠️ Creating database context: '{db_name}'...")
                if db_name not in existing_dbs:
                    cursor.execute(f"CREATE DATABASE {db_name};")
                    print(f"   ✅ Database '{db_name}' created successfully.")
                else:
                    print(f"   ℹ️ Database '{db_name}' already exists.")
        conn.close()

        # 2. Connect to each newly created database and initialize the Apache AGE extension and correct graph name
        db_graphs = {
            "keyword_db": "keyword_graph",
            "memory_db": "rdf_quadstore_graph"
        }
        
        for db_name, graph_name in db_graphs.items():
            print(f"⚙️ Initializing Apache AGE extension in database '{db_name}'...")
            db_conn = psycopg2.connect(
                host=PG_HOST,
                port=PG_PORT,
                database=db_name,
                user=PG_USER,
                password=PG_PASSWORD
            )
            db_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            with db_conn.cursor() as db_cursor:
                # Load the Apache AGE extension
                db_cursor.execute("CREATE EXTENSION IF NOT EXISTS age;")
                db_cursor.execute("LOAD 'age';")
                db_cursor.execute("SET search_path = ag_catalog, '$user', public;")
                
                # Create the corresponding graph inside the database
                try:
                    db_cursor.execute(f"SELECT create_graph('{graph_name}');")
                    print(f"   ✅ Apache AGE extension and '{graph_name}' initialized in '{db_name}'.")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print(f"   ℹ️ '{graph_name}' already exists in '{db_name}'.")
                    else:
                        print(f"   ⚠️ Warning initializing graph in '{db_name}': {e}")
            db_conn.close()
            
        print("\n🎉 Apache AGE database context setup complete!")
    except Exception as e:
        print(f"\n❌ Error setting up databases: {e}")

if __name__ == "__main__":
    main()
