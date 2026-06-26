# 🚨 Post-Mortem & Troubleshooting Guide: Memgraph, Podman & WSL2 Networking

This document provides a post-mortem of the technical issues that stalled local database integration and port connectivity under the **Alpine WSL + Podman** environment on Windows, along with steps to rebuild the system cleanly.

---

## 🔍 Part 1: The Core Issues & Diagnostic Analysis

During database setup and integration tests, we faced four overlapping network, system, and permission issues.

### 1. WSL2 Automatic VM Idle Shutdown (Unmounting Filesystems)
* **The Problem:** On Windows, WSL2 automatically shuts down and unmounts the guest Linux VM if it detects no active interactive shells or foreground processes for a short period (typically 15–60 seconds). Because `start_infra.py` starts containers in the background (`-d`) and exits immediately, WSL2 classified the VM as idle and terminated it while the Python integration tests were running.
* **The Symptom:** In Windows, socket connections to `localhost:7687` suddenly returned `b''` or raised `ConnectionRefusedError`. Checking `dmesg` inside Alpine WSL showed:
  ```text
  Exception: Operation canceled @p9io.cpp:258 (AcceptAsync)
  EXT4-fs (sdc): unmounting filesystem.
  ```

### 2. Port Binding Isolation inside Podman Pods (`--infra=false`)
* **The Problem:** By default, `podman-compose` groups all containers of a project into a single shared Podman pod. However, it configures this pod with `--infra=false` (no infra/pause container). In Podman, the port mappings are handled by the infra container. Without it, the port mappings defined in `compose.yaml` fail to bind to the guest OS interfaces.
* **The Symptom:** `netstat -lntp` inside Alpine WSL showed no listener on ports `3000` or `7687`, even though `podman ps` claimed the ports were mapped (`0.0.0.0:7687->7687`). The host ports were entirely unreachable.

### 3. Dynamic `iptables` NAT Table Pollution
* **The Problem:** When containers or pods are forcefully terminated, crash, or the VM is unmounted abruptly, Podman's network driver (`Netavark`) sometimes fails to clean up its dynamic port-forwarding rules in the `iptables` `nat` table. These stale rules remain stored in the kernel.
* **The Symptom:** Even after deleting old containers, new containers could not receive traffic. Running `iptables -t nat -L -n -v` showed that incoming traffic to ports `3000` and `7687` was being hijacked by stale `DNAT` rules matching old container IDs and redirecting packets to non-existent container IPs (e.g. `10.89.0.6` instead of the active `10.89.0.2`), causing `incomplete handshake response` errors.

### 4. WSL Data Volume Permissions Mismatch (DrvFs)
* **The Problem:** Bind-mounting a Windows directory (`./data/memgraph`) inside WSL mounts it via DrvFs. By default, DrvFs maps all files to the `root` user. Memgraph, however, runs as the non-root `memgraph` user inside the container and has a strict directory ownership check:
  ```text
  Assertion failed in durability.cpp.
  Expression: 'process_euid == directory_owner'
  Message: 'The process is running as user memgraph, but the data directory is owned by user root.'
  ```
* **The Symptom:** The container entered a `FATAL` state and kept restarting or crashing with exit code `134` (SIGABRT) immediately on start.

---

## 🛠️ Part 2: The Applied Solutions & Architecture Upgrades

We resolved these issues by modifying the infrastructure configuration, helper scripts, and integration test setup:

1. **WSL VM Keep-Alive (Integration Test):**
   In `Tests/test_memgraph_sample.py`, we launch a background `wsl sleep 300` session via `subprocess.Popen` before executing tests and terminate it in a `finally` block. This keeps the WSL VM active, preventing automatic idle shutdown during test execution.
2. **Disabled Shared Pods (`--in-pod false`):**
   Updated `start_infra.py` and `stop_infra.py` to invoke `podman-compose --in-pod false`. This bypasses Podman pods and runs containers directly, allowing conmon to correctly bind `0.0.0.0:7687` and `0.0.0.0:3000` on the WSL host.
3. **NAT Table Flush:**
   Implemented manual flushing of `iptables` tables (`iptables -t nat -F && iptables -t nat -X`) to purge stale redirection rules.
4. **Named volumes for Memgraph:**
   Configured `memgraph-data` as a Podman-managed named volume in `compose.yaml` instead of a bind mount. Named volumes are native Linux mountpoints within WSL's ext4 filesystem, permitting standard ownership (`memgraph:memgraph`) and resolving container permissions.
5. **Path Resolution Fixes:**
   Corrected `PROJECT_ROOT` path resolution inside `start_infra.py` and `stop_infra.py` to use `.parent.parent.parent` so they correctly resolve the root `backend/` folder from `Scripts/infra/`.
6. **Robust Connections & Output Streams:**
   Removed `sys.stdout.reconfigure` calls (which hang under pytest captures) and created a `safe_print` utility to convert emojis safely under Windows console Turkish codepages (`cp1254`). Implemented a 10-attempt retry connection loop for Bolt client verification.

---

## 🚀 Part 3: How to Recreate/Reset the System Cleanly

If the container network or state becomes corrupt in the future, follow these steps to reset and recreate the system:

### Step 1: Terminate the WSL VM
This stops all active processes and flushes memory-mapped iptables rules.
```powershell
wsl --terminate alpine-rag
```

### Step 2: Boot WSL and Clean Up Container/Network State
Boot into Alpine WSL as root and run the following commands to forcefully remove leftover containers, pods, networks, and flush network tables:
```bash
# Enter WSL
wsl -d alpine-rag -u root

# Inside Alpine: Stop and delete all containers and pods
podman rm -f -a
podman pod rm -f -a

# Delete the default bridge network to wipe netavark configurations
podman network rm -f infra_default

# Flush and delete all custom nat tables (Crucial to clear stale port-forward rules)
iptables -t nat -F
iptables -t nat -X

# Exit WSL
exit
```

### Step 3: Run the Helper Script or pytest
Now start the stack cleanly. The network and iptables will be initialized correctly:
```powershell
# To manually run the start helper:
python Scripts/infra/start_infra.py

# Or run the integration test directly:
uv run pytest Tests/test_memgraph_sample.py -s
```
