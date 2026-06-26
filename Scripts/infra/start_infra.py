"""Start the Alpine WSL environment and Podman container stack.

Usage (from project root):
	python Scripts/start_infra.py
"""

import sys
import subprocess
from pathlib import Path

# Configure stdout/stderr to use UTF-8 to support rich emojis on Windows
if sys.stdout.encoding != 'utf-8':
	try:
		sys.stdout.reconfigure(encoding='utf-8')
	except AttributeError:
		pass
if sys.stderr.encoding != 'utf-8':
	try:
		sys.stderr.reconfigure(encoding='utf-8')
	except AttributeError:
		pass

# Add backend directory to Python path if running script directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))


def run_command(cmd: list[str]) -> subprocess.CompletedProcess:
	"""Helper to run command and return result."""
	return subprocess.run(
		cmd,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		text=True,
		encoding="utf-8",
	)


def to_wsl_path(win_path: Path) -> str:
	"""Translate a Windows path to a WSL path (e.g., C:\\path -> /mnt/c/path)."""
	abs_path = win_path.resolve()
	parts = list(abs_path.parts)
	drive = parts[0].replace("\\", "").replace(":", "").lower()
	wsl_parts = ["/mnt", drive] + parts[1:]
	return "/".join(wsl_parts)


def configure_wsl_limits() -> None:
	"""Ensure WSL memory is capped to 4GB in ~/.wslconfig."""
	wslconfig_path = Path.home() / ".wslconfig"
	config_content = "[wsl2]\nmemory=4GB\nprocessors=4\nswap=0\n"

	if not wslconfig_path.exists():
		try:
			wslconfig_path.write_text(config_content, encoding="utf-8")
			print("⚙️ Created ~/.wslconfig and set WSL RAM cap to 4GB (Processors: 4, Swap: Disabled).")
		except Exception as e:
			print(f"⚠️ Warning: Could not create ~/.wslconfig: {e}")
		return

	try:
		content = wslconfig_path.read_text(encoding="utf-8")
		if "memory" not in content:
			if "[wsl2]" in content:
				content = content.replace("[wsl2]", "[wsl2]\nmemory=4GB\nprocessors=4\nswap=0")
			else:
				content += "\n[wsl2]\nmemory=4GB\nprocessors=4\nswap=0\n"
			wslconfig_path.write_text(content, encoding="utf-8")
			print("⚙️ Updated ~/.wslconfig to set WSL RAM cap to 4GB.")
	except Exception as e:
		print(f"⚠️ Warning: Could not read/update ~/.wslconfig: {e}")


def main() -> None:
	print("🏔️ Starting Alpine WSL Podman stack...")

	# 0. Configure memory limits on host if not already set
	configure_wsl_limits()

	# 1. Sync custom configurations from infra/config to /etc/containers inside WSL
	config_dir = PROJECT_ROOT / "infra" / "config"
	wsl_rootfs_dest = "/etc/containers/"
	
	config_files = ["registries.conf", "policy.json", "storage.conf"]
	
	print("⚙️ Syncing Podman configuration files...")
	for config_file in config_files:
		src_path = config_dir / config_file
		if src_path.exists():
			wsl_src = to_wsl_path(src_path)
			cp_cmd = ["wsl", "-d", "alpine-rag", "-u", "root", "-e", "cp", wsl_src, wsl_rootfs_dest]
			res = run_command(cp_cmd)
			if res.returncode != 0:
				print(f"⚠️ Warning: Failed to sync configuration {config_file}: {res.stderr.strip()}", file=sys.stderr)
			else:
				print(f"   Synced: {config_file}")
		else:
			print(f"ℹ️ Config file {config_file} not found in infra/config. Skipping sync.")

	# 2. Boot up podman-compose up -d
	print("🐳 Bringing up podman-compose services (Memgraph, Typesense, Kafka)...")
	wsl_infra_dir = to_wsl_path(PROJECT_ROOT / "infra")
	compose_cmd = [
		"wsl",
		"-d",
		"alpine-rag",
		"-u",
		"root",
		"-e",
		"sh",
		"-c",
		f"cd {wsl_infra_dir} && podman-compose --in-pod false up -d"
	]
	
	res = run_command(compose_cmd)
	if res.returncode != 0:
		print(f"❌ Error starting containers: {res.stderr.strip()}", file=sys.stderr)
		sys.exit(res.returncode)
		
	print(res.stdout.strip())
	
	# 3. Check status
	print("\n📊 Current Container Status:")
	status_cmd = ["wsl", "-d", "alpine-rag", "-u", "root", "-e", "podman", "ps"]
	res = run_command(status_cmd)
	if res.returncode == 0:
		print(res.stdout)
	else:
		print("⚠️ Failed to check container status.")
		
	print("✅ System successfully started and ready!")


if __name__ == "__main__":
	main()
