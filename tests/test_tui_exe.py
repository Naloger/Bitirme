"""Test script to verify the EXE works correctly."""

import subprocess
import sys
import time
import os

exe_path = r"../dist/run_TUI.exe"

print("Testing the EXE application...")
print(f"Path: {exe_path}")
print(f"Exists: {os.path.exists(exe_path)}")

try:
    print("\nStarting application...")
    process = subprocess.Popen(
        [exe_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    # Wait a moment for the app to start
    time.sleep(3)

    # Check if process is still running
    if process.poll() is None:
        print("✓ Application started successfully!")
        print("  Process is running...")
        process.terminate()
        print("  Process terminated.")
    else:
        stdout, stderr = process.communicate()
        print("✗ Application exited immediately")
        if stderr:
            print(f"\nError output:\n{stderr}")
        if stdout:
            print(f"\nStandard output:\n{stdout}")
        sys.exit(1)

except Exception as e:
    print(f"✗ Error running application: {e}")
    sys.exit(1)

print("\n✓ Test completed successfully!")
