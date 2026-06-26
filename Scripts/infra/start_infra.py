"""Start the Alpine WSL environment and Podman container stack.

Usage (from project root):
	python Scripts/start_infra.py
"""

import sys
import subprocess
from pathlib import Path

# Configure stdout/stderr to use UTF-8 to support rich emojis on Windows
if sys.stdout.encoding != 'utf-8':
	reconfigure_stdout = getattr(sys.stdout, 'reconfigure', None)
	if reconfigure_stdout:
		try:
			reconfigure_stdout(encoding='utf-8')
		except Exception:
			pass
if sys.stderr.encoding != 'utf-8':
	reconfigure_stderr = getattr(sys.stderr, 'reconfigure', None)
	if reconfigure_stderr:
		try:
			reconfigure_stderr(encoding='utf-8')
		except Exception:
			pass

# Add backend directory to Python path if running script directly
# The script is located in Scripts/infra/, so we go up three levels to reach the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))


def run_command(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
	"""Helper to run command and return result."""
	res = subprocess.run(
		cmd,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		text=True,
		encoding="utf-8",
	)
	if check and res.returncode != 0:
		raise subprocess.CalledProcessError(
			returncode=res.returncode,
			cmd=cmd,
			output=res.stdout,
			stderr=res.stderr,
		)
	return res


def to_wsl_path(win_path: Path) -> str:
	"""Translate a Windows path to a WSL path (e.g., C:\\path -> /mnt/c/path)."""
	abs_path = win_path.resolve()
	drive = abs_path.drive.rstrip(":").lower()
	wsl_parts = ["/mnt", drive] + list(abs_path.parts[1:])
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
		lines = content.splitlines()
		in_wsl2 = False
		wsl2_section_index = -1
		existing_keys = set()

		for idx, line in enumerate(lines):
			line_strip = line.strip()
			if line_strip.startswith("#") or line_strip.startswith(";"):
				continue
			if line_strip.startswith("[") and line_strip.endswith("]"):
				if line_strip.lower() == "[wsl2]":
					in_wsl2 = True
					wsl2_section_index = idx
				else:
					in_wsl2 = False
			elif in_wsl2:
				parts = line_strip.split("=", 1)
				if len(parts) == 2:
					key = parts[0].strip().lower()
					existing_keys.add(key)

		to_insert = []
		if "memory" not in existing_keys:
			to_insert.append("memory=4GB")
		if "processors" not in existing_keys:
			to_insert.append("processors=4")
		if "swap" not in existing_keys:
			to_insert.append("swap=0")

		if to_insert:
			if wsl2_section_index != -1:
				# Insert the missing settings right below the [wsl2] header
				for setting in reversed(to_insert):
					lines.insert(wsl2_section_index + 1, setting)
				wslconfig_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
				print(f"⚙️ Updated ~/.wslconfig [wsl2] section with missing settings: {', '.join(to_insert)}")
			else:
				# Append [wsl2] section if missing entirely
				new_content = content.rstrip() + "\n\n[wsl2]\n" + "\n".join(to_insert) + "\n"
				wslconfig_path.write_text(new_content, encoding="utf-8")
				print("⚙️ Created [wsl2] section in ~/.wslconfig with RAM cap and other settings.")
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

	# 1.5. Flush any stale NAT rules from previous runs to prevent connection hijacking
	print("🧹 Flushing stale network NAT rules...")
	run_command(["wsl", "-d", "alpine-rag", "-u", "root", "-e", "sh", "-c", "iptables -t nat -F && iptables -t nat -X"])

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
	
	try:
		res = run_command(compose_cmd, check=True)
		print(res.stdout.strip())
	except subprocess.CalledProcessError as e:
		print(f"❌ Error starting containers: {e.stderr.strip() if e.stderr else str(e)}", file=sys.stderr)
		sys.exit(e.returncode)
	
	# 3. Check status
	print("\n📊 Current Container Status:")
	status_cmd = ["wsl", "-d", "alpine-rag", "-u", "root", "-e", "podman", "ps"]
	res = run_command(status_cmd)
	if res.returncode == 0:
		print(res.stdout)
	else:
		print("⚠️ Failed to check container status.")

	# 4. Launch a background keep-alive session inside WSL to prevent idle shutdown
	print("\n📌 Starting background keep-alive session inside WSL...")
	try:
		# Run a detached sleep process inside WSL using nohup to keep WSL awake.
		# We check if a 'sleep infinity' process is already running to avoid leaking
		# multiple sleep processes on repeated start_infra.py runs.
		res = run_command([
			"wsl", "-d", "alpine-rag", "-u", "root", "-e", "sh", "-c",
			"pgrep -f 'sleep infinity' >/dev/null || nohup sleep infinity >/dev/null 2>&1 &"
		])
		if res.returncode == 0:
			print("   Keep-alive session started. WSL will remain active until you run stop_infra.py.")
		else:
			print(f"⚠️ Warning: Failed to start keep-alive session: {res.stderr.strip()}")
	except Exception as e:
		print(f"⚠️ Warning: Could not start keep-alive session: {e}")
		
	print("\n✅ System successfully started and ready!")


if __name__ == "__main__":
	main()
