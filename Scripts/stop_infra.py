"""Stop the Podman container stack and terminate the Alpine WSL environment.

Usage (from project root):
	python Scripts/stop_infra.py
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
PROJECT_ROOT = Path(__file__).resolve().parent.parent
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


def main() -> None:
	print("🛑 Stopping Alpine WSL Podman stack...")

	# 1. Shut down podman-compose
	print("🐳 Stopping container services...")
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
		f"cd {wsl_infra_dir} && podman-compose down"
	]
	
	res = run_command(compose_cmd)
	if res.returncode != 0:
		# If the containers are already down or wsl is stopped, it might return non-zero
		print(f"ℹ️ Note: Podman compose down output: {res.stderr.strip() or res.stdout.strip()}")
	else:
		print("✅ Container services successfully stopped.")

	# 2. Terminate the WSL environment to free host RAM
	print("🏔️ Shutting down Alpine WSL distribution to free system memory...")
	terminate_cmd = ["wsl", "--terminate", "alpine-rag"]
	
	res = run_command(terminate_cmd)
	if res.returncode != 0:
		print(f"❌ Error terminating WSL: {res.stderr.strip()}", file=sys.stderr)
		sys.exit(res.returncode)
		
	print("✅ Alpine WSL environment terminated successfully!")


if __name__ == "__main__":
	main()
