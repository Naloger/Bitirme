import sys
import psycopg2

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


def main():
    print(f"🔌 Connecting to PostgreSQL at {PG_HOST}:{PG_PORT}...")
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DB,
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

if __name__ == "__main__":
    main()
