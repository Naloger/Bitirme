import subprocess
import sys
import time
from pathlib import Path
import pytest
from neo4j import GraphDatabase

def safe_print(text: str):
    """Safely prints strings containing emojis without crashing on restricted Windows console codepages."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or 'utf-8'
        print(text.encode(encoding, errors='replace').decode(encoding))

# Define Memgraph Bolt URI
MEMGRAPH_URI = "bolt://127.0.0.1:7687"

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


def test_create_sample_memgraph_data():
    # Keep WSL VM alive during the test to prevent automatic idle shutdown
    print("[INFO] Keeping WSL VM alive with a background session...")
    wsl_session = subprocess.Popen(
        ["wsl", "-d", "alpine-rag", "sleep", "300"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    try:
        # 1. Run start script to bring up podman containers
        run_infra_start_script()
        
        # 2. Wait a few seconds for services to initialize and bind ports
        print("[INFO] Waiting for Memgraph service to initialize...")
        time.sleep(2)

        # 3. Attempt connection to Memgraph with retries
        print(f"[INFO] Connecting to Memgraph at {MEMGRAPH_URI}...")
        driver = None
        max_retries = 10
        for attempt in range(1, max_retries + 1):
            try:
                driver = GraphDatabase.driver(MEMGRAPH_URI, auth=("", ""))
                driver.verify_connectivity()
                print(f"[SUCCESS] Connected to Memgraph on attempt {attempt}!")
                break
            except Exception as e:
                print(f"[INFO] Connection attempt {attempt}/{max_retries} failed: {e}. Retrying in 3s...")
                time.sleep(3)
        else:
            pytest.fail(
                f"[ERROR] Failed to connect to Memgraph at {MEMGRAPH_URI} after {max_retries} attempts. "
                f"Ensure Podman is running and Alpine WSL is active."
            )

        # 4. Clear existing data and write sample graph
        with driver.session() as session:
            # Clear database
            print("[INFO] Clearing database...")
            session.run("MATCH (n) DETACH DELETE n")

            # Create sample NLP/Concept Graph
            print("[INFO] Creating sample data in Memgraph...")
            create_query = """
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
            """
            session.run(create_query)

            # 5. Assert the graph was created successfully
            print("[INFO] Verifying created nodes...")
            result = session.run("MATCH (n:Concept) RETURN count(n) as count")
            count = result.single()["count"]
            
            assert count == 8, f"Expected 8 Concept nodes, but found {count}."
            print(f"[SUCCESS] Created {count} Concept nodes in Memgraph.")
            
            # Print sample node details for validation
            nodes = session.run("MATCH (n:Concept) RETURN n.name as name, n.category as category LIMIT 3")
            print("\nSample Created Concepts:")
            for record in nodes:
                print(f" - {record['name']} ({record['category']})")

        driver.close()

    finally:
        print("[INFO] Terminating WSL keep-alive session...")
        wsl_session.terminate()
        wsl_session.wait()
