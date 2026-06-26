# 🏔️ Local Setup: Alpine WSL + Podman on Windows

Because native `podman-static` binaries are built for Linux, they cannot run directly on Windows host command prompt. Instead, we can import a lightweight **Alpine Linux** distribution into Windows Subsystem for Linux (WSL).

This approach:
* Requires **no installation of Docker Desktop or Podman Desktop**.
* Runs in a completely isolated, lightweight WSL environment (~15MB RAM footprint for the OS).
* Automatically forwards ports (`9092`, `7687`, `3000`, `8108`) to `localhost` on Windows, so your Python scripts and agents can connect seamlessly.

---

## 📂 Updated Folder Structure

We have adapted the folder structure to support the WSL environment:

```
backend/ (Project Root)
│
├── infra/
│   ├── engine/
│   │   └── wsl/                    # Place the Alpine rootfs .tar.gz file here
│   │
│   ├── config/                     # Configuration overrides if needed
│   │
│   ├── images/                     # Put offline container images (.tar) here
│   │
│   ├── data/                       # Local database persistent volumes
│   │   ├── typesense/
│   │   ├── memgraph/
│   │   └── kafka/
│   │
│   ├── compose.yaml                # Orchestration script (Typesense, Memgraph, Kafka)
│   └── setup-alpine.md             # This instruction guide
```

---

## 🛠️ Step-by-Step Guide

### Step 1: Download Alpine WSL RootFS
1. Download the latest **Alpine Linux Mini Root Filesystem** (x86_64 architecture) from the [Alpine Downloads page](https://alpinelinux.org/downloads/).
   * Look for the **"MINI ROOT FILESYSTEM"** section.
   * Download the file named like: `alpine-minirootfs-3.20.0-x86_64.tar.gz`.
2. Move the downloaded `.tar.gz` file to your project's **`infra/engine/wsl/`** directory.

---

### Step 2: Import Alpine Distro into WSL
Open a standard Windows **Command Prompt (cmd)** or **PowerShell** at your project root directory and run the following commands:

```powershell
# 1. Create a directory to host Alpine's virtual disk file
mkdir infra\engine\wsl\distro

# 2. Import the distro into WSL as "alpine-rag"
# NOTE: WSL --import does not support wildcards (*) and works best with absolute paths.
# Replace the paths below with the absolute path to your project directory and the exact filename of your downloaded tar.gz.
wsl --import alpine-rag "C:\CalismaAlani\CodingPython\Bitirme\backend\infra\engine\wsl\distro" "C:\CalismaAlani\CodingPython\Bitirme\backend\infra\engine\wsl\alpine-minirootfs-3.24.1-x86_64.tar.gz" --version 2
```

---

### Step 3: Configure Alpine & Install Podman
Now boot into the newly imported Alpine Linux distribution:

```powershell
# Enter the Alpine environment as root
wsl -d alpine-rag -u root
```

Inside the Alpine Linux terminal, run these commands to install Podman and Compose:

```bash
# 1. Update package registry
apk update

# 2. Install Podman, Podman-Compose, and dependencies (including iptables for container networking NAT)
apk add podman podman-compose shadow libc6-compat iptables

# 3. Enable network packet forwarding (crucial for container networking)
# Note: BusyBox's sysctl on Alpine does not support --system. Use /etc/sysctl.conf and sysctl -p.
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p
```

---

### Step 4: Run the Compose Stack
WSL automatically mounts your Windows drives under `/mnt/`. Your project root `C:\CalismaAlani\CodingPython\Bitirme\backend` is accessible inside Alpine at:
`/mnt/c/CalismaAlani/CodingPython/Bitirme/backend`

To start the database stack, run this command inside the Alpine shell:

```bash
# Navigate to the project's infra directory
cd /mnt/c/CalismaAlani/CodingPython/Bitirme/backend/infra

# Start the stack
podman-compose up -d
```

---

## 🐳 Running Offline / Pre-downloaded Images (Optional)
If you need to install container images offline:
1. Place the saved `.tar` images into `infra/images/` on Windows.
2. In the Alpine shell, load them into Podman:
   ```bash
   podman load -i /mnt/c/CalismaAlani/CodingPython/Bitirme/backend/infra/images/memgraph.tar
   podman load -i /mnt/c/CalismaAlani/CodingPython/Bitirme/backend/infra/images/typesense.tar
   podman load -i /mnt/c/CalismaAlani/CodingPython/Bitirme/backend/infra/images/kafka.tar
   ```

## 🚀 Easy Start & Stop Helper Scripts (Recommended)

To make it easy to start and stop the infrastructure stack without keeping WSL running in the background, we have created two portable Python helper scripts in the `Scripts/` folder:

* **Start the stack and sync configuration overrides**:
  ```powershell
  python Scripts/start_infra.py
  ```
  *(This automatically syncs configuration files from `infra/config` to WSL and boots up your database services).*

* **Stop the stack and release all system RAM**:
  ```powershell
  python Scripts/stop_infra.py
  ```
  *(This stops the container services and completely terminates the Alpine WSL distribution, freeing all host RAM).*

---

## 🛑 Useful Management Commands

Run these directly from your **Windows terminal**:

* **Shutdown the stack**: 
  `wsl -d alpine-rag -u root -e sh -c "cd /mnt/c/CalismaAlani/CodingPython/Bitirme/backend/infra && podman-compose down"`
* **Check service status**:
  `wsl -d alpine-rag -u root -e podman ps`
* **Stop Alpine VM to save RAM**:
  `wsl --terminate alpine-rag`
* **Unregister/Delete the Alpine environment (Full Reset)**:
  `wsl --unregister alpine-rag`
