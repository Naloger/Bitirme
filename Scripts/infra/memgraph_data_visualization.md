# 📊 Memgraph Data Visualization Guide

This guide explains how to visualize your Memgraph database data without bundling the Memgraph Lab UI directly in your project repository or main container orchestration stack.

Because the project runs on **Alpine WSL + Podman**, keeping the UI database visualizer out of the core services helps keep the development stack lightweight and separate.

---

## 🌐 Option 1: Hosted Web Client (No Installation)
The easiest way to visualize your graph is through the official hosted web version of Memgraph Lab. It runs entirely in your browser and connects directly to your local instance.

### Step-by-Step:
1. Ensure your Memgraph database container is running and port `7687` is mapped to your localhost.
2. Open your web browser and navigate to **[lab.memgraph.com](https://lab.memgraph.com/)**.
3. In the connection window, fill in the following details:
   - **Host:** `localhost`
   - **Port:** `7687`
   - **Username / Password:** (Leave empty by default)
4. Click **Connect**. Your browser will establish a direct secure Bolt connection to your local container.

---

## 💻 Option 2: Standalone Desktop App (Local Client)
If you prefer a native desktop application that does not run in a web browser, you can install the official standalone client.

### Step-by-Step:
1. Download **Memgraph Lab Desktop** from the [Memgraph Downloads page](https://memgraph.com/download).
2. Install and launch the application on your Windows machine.
3. On the startup screen, select **Connect to a remote database** or choose the standard connection card.
4. Set the connection settings to:
   - **Host:** `127.0.0.1` or `localhost`
   - **Port:** `7687`
5. Click **Connect**.

---

## 🐳 Option 3: Standalone Podman Container (Isolated Web UI)
If you want to run the web UI locally but keep it strictly isolated in its own separate container that can be started and stopped on-demand, you can run the standalone `memgraph/lab` image.

### Step-by-Step:

#### Method A: Shared Network Connection (Recommended)
If you run your containers on a shared Podman network (e.g., `memgraph-net`), they can communicate using container names.

1. **Create the network (if not already existing):**
   ```bash
   podman network create memgraph-net
   ```

2. **Run your Memgraph Database container:**
   ```bash
   podman run -d \
     --name memgraph-db \
     --network memgraph-net \
     -p 7687:7687 \
     -p 7444:7444 \
     memgraph/memgraph-mage:latest
   ```

3. **Run the Memgraph Lab UI container on the same network:**
   ```bash
   podman run -d \
     --name memgraph-lab \
     --network memgraph-net \
     -p 3000:3000 \
     memgraph/lab:latest
   ```

4. Open **`http://localhost:3000`** in your browser.
5. Connect using the container name as the hostname:
   - **Host:** `memgraph-db`
   - **Port:** `7687`

---

#### Method B: Standalone Container (Connecting via Host)
If your database container was started without a custom network but exposes port `7687` to your Windows host, you can route the Lab container connection through the host.

1. **Run the Lab container:**
   ```bash
   podman run -d \
     --name memgraph-lab \
     -p 3000:3000 \
     memgraph/lab:latest
   ```

2. Open **`http://localhost:3000`** in your browser.
3. Connect using the special container host loopback:
   - **Host:** `host.containers.internal` (or `host.docker.internal`)
   - **Port:** `7687`
