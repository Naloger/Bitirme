"""Stop the Podman container stack and terminate the Alpine WSL environment.

Usage (from project root):
	python Scripts/stop_infra.py
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
		f"cd {wsl_infra_dir} && podman-compose --in-pod false down"
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
	
	try:
		run_command(terminate_cmd, check=True)
		print("✅ Alpine WSL environment terminated successfully!")
	except subprocess.CalledProcessError as e:
		print(f"❌ Error terminating WSL: {e.stderr.strip() if e.stderr else str(e)}", file=sys.stderr)
		sys.exit(e.returncode)


if __name__ == "__main__":
	main()
