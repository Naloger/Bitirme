# 📊 Apache AGE Data Visualization and Administration

This guide explains how to connect to, query, and visualize your **Apache AGE** (PostgreSQL-based Graph DB) instance.

---

## 🔌 Connection Details
* **Host**: `127.0.0.1` (mapped from Podman inside WSL)
* **Port**: `5432`
* **Username**: `postgres`
* **Password**: `local_rag_secret_key_123`
* **Database**: `graphdb`

---

## 🛠️ Recommended Administration Tools

### 1. DBeaver (Highly Recommended)
DBeaver is a free multi-platform database tool that supports PostgreSQL out of the box and handles JSON/agtype parsing cleanly.
1. Download and install [DBeaver Community Edition](https://dbeaver.io/).
2. Create a new connection: Select **PostgreSQL**.
3. Enter the connection details above.
4. Open a SQL Editor and execute Cypher queries wrapped in the `cypher()` function (see examples below).

### 2. pgAdmin 4
pgAdmin is the official web/desktop administration tool for PostgreSQL.
1. Download from [pgAdmin download page](https://www.pgadmin.org/download/).
2. Connect to server `127.0.0.1:5432` using password `local_rag_secret_key_123`.

---

## 📝 Querying Cypher in PostgreSQL SQL Editor

Since Apache AGE is a PostgreSQL extension, Cypher queries must be wrapped in PostgreSQL `SELECT` functions.

### 1. Initialize the Session (Run this in every new editor tab)
To load the AGE extension and configure the search path:
```sql
LOAD 'age';
SET search_path = ag_catalog, "$user", public;
```

### 2. Querying Nodes and Relationships
To query concepts in the graph:
```sql
SELECT * FROM cypher('concept_graph', $$
    MATCH (n:Concept)-[r:RELATED_TO]->(m:Concept)
    RETURN n.name, type(r), m.name
$$) as (source_node agtype, relationship agtype, target_node agtype);
```

### 3. Adding New Nodes
```sql
SELECT * FROM cypher('concept_graph', $$
    CREATE (new_node:Concept {name: 'Apache AGE', category: 'Graph DB'})
$$) as (a agtype);
```
