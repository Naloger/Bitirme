import psycopg2
from psycopg2.extras import DictCursor
import subprocess
import sys
import time
from pathlib import Path
import pytest

def safe_print(text: str):
    """Safely prints strings containing emojis without crashing on restricted Windows console codepages."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or 'utf-8'
        print(text.encode(encoding, errors='replace').decode(encoding))

# Connection details for Apache AGE (PostgreSQL + AGE extension)
PG_HOST = "127.0.0.1"
PG_PORT = "5435"
PG_DB = "graphdb"
PG_USER = "postgres"
PG_PASSWORD = "local_rag_secret_key_123"

def run_infra_start_script():
    """Executes Scripts/infra/start_infra.py via subprocess to ensure container stack is up."""
    project_root = Path(__file__).resolve().parent.parent
    script_path = project_root / "Scripts" / "infra" / "start_infra.py"
    
    safe_print(f"\n[INFO] Booting infrastructure stack using: {script_path}...")
    res = subprocess.run(
        [sys.executable, str(script_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8"
    )
    
    if res.returncode != 0:
        safe_print(f"[WARN] start_infra.py returned exit code {res.returncode}.")
        safe_print(f"Error details:\n{res.stderr}")
    else:
        safe_print("[SUCCESS] start_infra.py executed successfully.")
        safe_print(res.stdout)


def test_create_sample_age_data():
    # 1. Run start script to bring up podman containers
    run_infra_start_script()
    
    # 2. Wait a few seconds for services to initialize and bind ports
    print("[INFO] Waiting for PostgreSQL/Apache AGE service to initialize...")
    time.sleep(3)

    # 3. Attempt connection to PostgreSQL/AGE with retries
    print(f"[INFO] Connecting to Apache AGE at {PG_HOST}:{PG_PORT}...")
    conn = None
    max_retries = 10
    for attempt in range(1, max_retries + 1):
        try:
            conn = psycopg2.connect(
                host=PG_HOST,
                port=PG_PORT,
                database=PG_DB,
                user=PG_USER,
                password=PG_PASSWORD
            )
            print(f"[SUCCESS] Connected to PostgreSQL on attempt {attempt}!")
            break
        except Exception as e:
            print(f"[INFO] Connection attempt {attempt}/{max_retries} failed: {e}. Retrying in 3s...")
            time.sleep(3)
    else:
        pytest.fail(
            f"[ERROR] Failed to connect to PostgreSQL at {PG_HOST}:{PG_PORT} after {max_retries} attempts. "
            f"Ensure Podman is running and Alpine WSL is active."
        )

    conn.autocommit = True
    with conn.cursor() as cursor:
        # 4. Initialize AGE extension in database
        print("[INFO] Initializing AGE extension...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS age;")
        cursor.execute("LOAD 'age';")
        cursor.execute("SET search_path = ag_catalog, '$user', public;")
        
        # 5. Drop old graph if exists and recreate
        print("[INFO] Dropping old graph...")
        try:
            cursor.execute("SELECT drop_graph('concept_graph', true);")
        except Exception:
            pass  # Graph might not exist
            
        print("[INFO] Creating new graph 'concept_graph'...")
        cursor.execute("SELECT create_graph('concept_graph');")

        # 6. Create sample nodes and edges using openCypher via cypher() SQL function
        print("[INFO] Inserting sample data into concept_graph...")
        create_query = """
        SELECT * FROM cypher('concept_graph', $$
            CREATE (nlp:Concept {name: 'Natural Language Processing', category: 'Field'})
            CREATE (we:Concept {name: 'Word Embedding', category: 'Methodology'})
            CREATE (w2v:Concept {name: 'Word2Vec', category: 'Algorithm'})
            CREATE (glove:Concept {name: 'GloVe', category: 'Algorithm'})
            CREATE (lm:Concept {name: 'Language Model', category: 'Field'})
            CREATE (trans:Concept {name: 'Transformer', category: 'Architecture'})
            CREATE (bert:Concept {name: 'BERT', category: 'Model'})
            CREATE (gpt:Concept {name: 'GPT', category: 'Model'})
            
            CREATE (nlp)-[:RELATED_TO]->(we)
            CREATE (we)-[:IMPLEMENTED_BY]->(w2v)
            CREATE (we)-[:IMPLEMENTED_BY]->(glove)
            CREATE (nlp)-[:RELATED_TO]->(lm)
            CREATE (lm)-[:USES]->(trans)
            CREATE (trans)-[:SPECIALIZED_AS]->(bert)
            CREATE (trans)-[:SPECIALIZED_AS]->(gpt)
        $$) as (a agtype);
        """
        cursor.execute(create_query)

        # 7. Query and assert concept node counts
        print("[INFO] Querying Concept nodes count...")
        count_query = """
        SELECT * FROM cypher('concept_graph', $$
            MATCH (n:Concept) 
            RETURN count(n)
        $$) as (count agtype);
        """
        cursor.execute(count_query)
        row = cursor.fetchone()
        # Apache AGE returns agtype (which converts to string/JSON in standard psycopg)
        # We parse the result. Since count returns an integer represented in agtype, e.g. "8::int" or just 8
        assert row is not None
        count_val = str(row[0])
        # Parse standard integer from AGE output
        count = int(count_val.split("::")[0])
        assert count == 8, f"Expected 8 Concept nodes, but found {count} (raw: {count_val})."
        print(f"[SUCCESS] Created {count} Concept nodes in Apache AGE.")

        # 8. Query sample relations
        print("[INFO] Fetching sample relationships...")
        fetch_query = """
        SELECT * FROM cypher('concept_graph', $$
            MATCH (n:Concept)-[r:IMPLEMENTED_BY]->(m:Concept)
            RETURN n.name, m.name
        $$) as (source agtype, target agtype);
        """
        cursor.execute(fetch_query)
        rows = cursor.fetchall()
        print("\nSample IMPLEMENTED_BY Relationships:")
        for r in rows:
            # strip quotes or type casting indicators
            source_name = str(r[0]).strip('"')
            target_name = str(r[1]).strip('"')
            print(f" - {source_name} -> {target_name}")

    conn.close()
