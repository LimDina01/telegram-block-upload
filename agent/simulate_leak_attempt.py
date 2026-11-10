"""
Live Demonstration Simulator: Telegram 3D Leak Attempt
-------------------------------------------------------
This simulator proves the real-world effectiveness of the DLP Watchdog:
  1. Creates a sample 3D file (with binary FBX magic header).
  2. Spawns a mock process named 'Telegram.exe' to simulate an employee attempting an upload.
  3. The mock Telegram process opens a handle to the 3D file.
  4. The DLP Watchdog detects the open handle within ~150ms.
  5. The DLP Watchdog terminates the mock Telegram process, logs the violation, and triggers an alert.
"""

import os
import sys
import time
import shutil
import tempfile
import subprocess
from dlp_watchdog import DLPWatchdog, load_config

def main():
    print("=" * 65)
    print("  TELEGRAM 3D LEAK ATTEMPT - LIVE DEMONSTRATION")
    print("=" * 65)

    temp_dir = tempfile.mkdtemp(prefix="dlp_demo_")
    mock_telegram_exe = os.path.join(temp_dir, "Telegram.exe")
    fake_asset = os.path.join(temp_dir, "confidential_character.fbx")

    # 1. Create realistic binary FBX file
    with open(fake_asset, "wb") as f:
        # Standard Kaydara FBX binary header
        f.write(b"Kaydara FBX Binary  \x00\x1a\x00\x00\x00\x00\x00Sample Model Data...")

    print(f"[*] Step 1: Created test 3D asset at: {fake_asset}")

    # 2. Duplicate current python.exe to Telegram.exe
    shutil.copyfile(sys.executable, mock_telegram_exe)
    print(f"[*] Step 2: Spawned mock Telegram executable: {mock_telegram_exe}")

    # 3. Create a python script that will be executed by Telegram.exe
    mock_script = os.path.join(temp_dir, "worker.py")
    with open(mock_script, "w") as f:
        f.write(f"""
import time
print("[Mock Telegram] Attempting to read 3D asset for upload...")
# Hold file open to simulate reading and uploading
with open(r"{fake_asset}", "rb") as f:
    data = f.read(64)
    time.sleep(10) # Hold handle open for up to 10 seconds
""")

    print("[*] Step 3: Launching mock Telegram process...")
    proc = subprocess.Popen([mock_telegram_exe, mock_script])
    print(f"[*] Mock Telegram running with PID: {proc.pid}")

    print("[*] Step 4: Initializing DLP Watchdog to scan...")
    config = load_config()
    # Ensure popup is enabled for the demo
    config["show_user_popup"] = False  # Keep false in automated runner to avoid hanging on message box
    watchdog = DLPWatchdog(config)

    # Let the mock telegram open the file
    time.sleep(0.3)

    # Trigger watchdog scan cycle
    watchdog.scan_cycle()

    # Verify if mock telegram was killed
    time.sleep(0.5)
    poll_result = proc.poll()

    print("\n" + "=" * 65)
    if poll_result is not None:
        print(f"[SUCCESS] Mock Telegram (PID {proc.pid}) was DETECTED and TERMINATED by DLP!")
        print(f"[SUCCESS] Process exit code: {poll_result}")
    else:
        print("[!] Process still alive - terminating manually.")
        proc.kill()
    print("=" * 65)

    # Clean up
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

if __name__ == "__main__":
    main()

