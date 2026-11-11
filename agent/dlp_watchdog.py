"""
Telegram 3D File Upload DLP Watchdog Service
--------------------------------------------
Monitors Telegram (and other specified messaging/browser processes) in real-time.
If an unauthorized process attempts to read or upload sensitive 3D assets
(.fbx, .obj, .blend, .max, .ztl, etc.) or archive files, this watchdog:
  1. Immediately terminates the offending process (kill).
  2. Prevents the data transfer from finishing.
  3. Logs the security violation with timestamp, user, hash, and file path.
  4. Optionally sends an alert popup to the employee and sends a webhook to SecOps.
"""

import os
import sys
import time
import json
import socket
import logging
import hashlib
import threading
import ctypes
import subprocess
import urllib.request
from typing import Dict, Any, List, Optional
import psutil

# Windows API constants
MB_OK = 0x00000000
MB_ICONSTOP = 0x00000010
MB_SYSTEMMODAL = 0x00001000
MB_SERVICE_NOTIFICATION = 0x00200000

# Embedded Default Configuration (Used if no external config.json is present)
DEFAULT_CONFIG = {
    "mode": "whitelist",
    "target_processes": ["Telegram.exe", "TelegramInternal.exe"],
    "allowed_extensions": [
        ".png", ".jpg", ".jpeg", ".gif", ".webp",
        ".pdf", ".txt", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".csv"
    ],
    "blocked_extensions": [
        ".fbx", ".obj", ".blend", ".max", ".mb", ".ma", ".c4d",
        ".ztl", ".zpr", ".step", ".stp", ".iges", ".igs", ".3ds", ".3dm",
        ".stl", ".glb", ".gltf", ".dae", ".ply", ".abc", ".usd",
        ".zip", ".rar", ".7z", ".tar", ".gz"
    ],
    "magic_signatures": [
        {"name": "Rhino 3D Model", "hex_prefix": "3344204D6F64656C"},
        {"name": "Blender 3D Project", "hex_prefix": "424C454E444552"},
        {"name": "Kaydara FBX Binary", "hex_prefix": "4B617964617261204642582042696E617279"},
        {"name": "glTF Binary 3D", "hex_prefix": "676C5446"},
        {"name": "Windows Executable (EXE/DLL)", "hex_prefix": "4D5A"},
        {"name": "ZIP Archive", "hex_prefix": "504B0304"},
        {"name": "7-Zip Archive", "hex_prefix": "377ABCAF271C"},
        {"name": "RAR Archive", "hex_prefix": "526172211A07"}
    ],
    "sensitive_directories": [],
    "action": "kill",
    "show_user_popup": True,
    "poll_interval_ms": 50,
    "log_file": "dlp_violations.log",
    "webhook_url": "http://127.0.0.1:5000/api/report"
}

# Locate directory (works both in Python script and compiled PyInstaller .exe)
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")


def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def setup_logger(log_file_path: str) -> logging.Logger:
    logger = logging.getLogger("DLP_Watchdog")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", %(message)s}'
    )

    # File handler (full path or relative to script dir)
    if not os.path.isabs(log_file_path):
        log_file_path = os.path.join(SCRIPT_DIR, log_file_path)

    fh = logging.FileHandler(log_file_path, encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
    logger.addHandler(ch)

    return logger


def show_alert_popup(title: str, message: str) -> None:
    """Displays a modal alert box on the active Windows desktop."""
    def _popup():
        try:
            flags = MB_OK | MB_ICONSTOP | MB_SYSTEMMODAL | MB_SERVICE_NOTIFICATION
            ctypes.windll.user32.MessageBoxW(0, message, title, flags)
        except Exception as e:
            print(f"[ERROR] Failed to show Windows popup: {e}", file=sys.stderr)

    thread = threading.Thread(target=_popup, daemon=True)
    thread.start()


def get_file_header_hex(file_path: str, byte_count: int = 32) -> Optional[str]:
    """Reads the first N bytes of a file to inspect magic signatures."""
    try:
        with open(file_path, "rb") as f:
            data = f.read(byte_count)
            return data.hex().upper()
    except Exception:
        return None


def calculate_partial_sha256(file_path: str, max_bytes: int = 1024 * 1024) -> str:
    """Calculates SHA-256 for auditing purposes (up to 1MB)."""
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(max_bytes)
            hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return "UNKNOWN_ACCESS_LOCKED"


def check_magic_signature(file_path: str, magic_signatures: List[Dict[str, str]]) -> Optional[str]:
    """Inspects file magic bytes to detect disguised files (e.g. .fbx renamed to .txt)."""
    hex_header = get_file_header_hex(file_path, 32)
    if not hex_header:
        return None

    for sig in magic_signatures:
        target_hex = sig.get("hex_prefix", "").upper()
        if target_hex and hex_header.startswith(target_hex):
            return sig.get("name", "Unknown 3D / Archive format")
    return None


class IncidentReporter:
    """
    Asynchronous Incident Dispatcher with Smart Offline Buffer.
    - Delivers incident JSON to the Central Management Dashboard via HTTP POST.
    - If server is offline, securely queues incidents locally in a capped buffer (max 50 events, <=15KB).
    - Automatically drains the buffer and delivers all pending logs when the server starts.
    """
    def __init__(self, webhook_url: str, cache_dir: str, max_buffer_size: int = 50):
        self.webhook_url = webhook_url
        self.max_buffer_size = max_buffer_size
        self.lock = threading.Lock()
        self.wake_event = threading.Event()
        self.running = True

        # Cache file path in script directory or user temp
        try:
            self.cache_file = os.path.join(cache_dir, "pending_dlp_events.json")
            with open(self.cache_file, "a", encoding="utf-8") as _:
                pass
        except Exception:
            fallback = os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", cache_dir))
            self.cache_file = os.path.join(fallback, "pending_dlp_events.json")

        self.queue: List[Dict[str, Any]] = self._load_cache()

        # Start background worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def _load_cache(self) -> List[Dict[str, Any]]:
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data[-self.max_buffer_size:]
        except Exception:
            pass
        return []

    def _save_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.queue, f)
        except Exception:
            pass

    def enqueue(self, event: Dict[str, Any]):
        if not self.webhook_url:
            return
        with self.lock:
            self.queue.append(event)
            # Strictly enforce max buffer size (FIFO drop oldest so it never gets heavy)
            if len(self.queue) > self.max_buffer_size:
                self.queue = self.queue[-self.max_buffer_size:]
            self._save_cache()
        # Wake up worker to send immediately
        self.wake_event.set()

    def _worker_loop(self):
        import urllib.request
        while self.running:
            if not self.webhook_url:
                time.sleep(5)
                continue

            event_to_send = None
            with self.lock:
                if self.queue:
                    event_to_send = self.queue[0]

            if not event_to_send:
                self.wake_event.wait(timeout=5)
                self.wake_event.clear()
                continue

            # Attempt delivery to server (tries configured URL, auto-fallbacks to loopback if local)
            urls_to_try = [self.webhook_url]
            if "127.0.0.1" not in self.webhook_url and "localhost" not in self.webhook_url:
                urls_to_try.append("http://127.0.0.1:5000/api/report")

            delivered = False
            for target_url in urls_to_try:
                try:
                    req = urllib.request.Request(
                        target_url,
                        data=json.dumps(event_to_send).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req, timeout=2) as resp:
                        if resp.status in (200, 201):
                            delivered = True
                            break
                except Exception:
                    continue

            if delivered:
                with self.lock:
                    if self.queue and self.queue[0] == event_to_send:
                        self.queue.pop(0)
                        self._save_cache()
                # Deliver next pending event without delay
                continue
            else:
                # Server offline, sleep 5 seconds before retrying
                time.sleep(5)


def protect_current_process():
    """
    Hardens this process's Security Descriptor (DACL) to DENY PROCESS_TERMINATE rights.
    When an employee opens Task Manager and clicks 'End Task', Windows blocks them
    with 'Access is Denied. Unable to terminate process.'
    """
    try:
        advapi32 = ctypes.windll.advapi32
        kernel32 = ctypes.windll.kernel32
        WRITE_DAC = 0x00040000
        DACL_SECURITY_INFORMATION = 4
        SDDL_REVISION_1 = 1

        pid = kernel32.GetCurrentProcessId()
        hProcess = kernel32.OpenProcess(WRITE_DAC, False, pid)
        if hProcess:
            pSD = ctypes.wintypes.LPVOID()
            # Explicitly DENY PROCESS_TERMINATE (0x0001) to Everyone (WD)
            sddl = "D:(D;;0x0001;;;WD)(A;;0x1FFFFF;;;SY)(A;;0x1FFFFF;;;BA)"
            if advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                sddl, SDDL_REVISION_1, ctypes.byref(pSD), None
            ):
                advapi32.SetKernelObjectSecurity(hProcess, DACL_SECURITY_INFORMATION, pSD)
            kernel32.CloseHandle(hProcess)
    except Exception:
        pass


class DLPWatchdog:
    def __init__(self, config: Dict[str, Any]):
        protect_current_process()
        self.config = config
        self.mode = config.get("mode", "whitelist").lower()
        self.target_processes = {p.lower() for p in config.get("target_processes", [])}
        self.allowed_extensions = {ext.lower() for ext in config.get("allowed_extensions", [])}
        self.blocked_extensions = {ext.lower() for ext in config.get("blocked_extensions", [])}
        self.magic_signatures = config.get("magic_signatures", [])
        self.sensitive_directories = [
            os.path.abspath(d).lower() for d in config.get("sensitive_directories", []) if d
        ]
        self.action = config.get("action", "kill").lower()
        self.show_popup = config.get("show_user_popup", True)
        self.poll_interval = max(0.05, config.get("poll_interval_ms", 150) / 1000.0)
        self.logger = setup_logger(config.get("log_file", "dlp_violations.log"))
        self.webhook_url = config.get("webhook_url", "")
        self.hostname = socket.gethostname()
        self.reporter = IncidentReporter(self.webhook_url, SCRIPT_DIR) if self.webhook_url else None

    def is_violation(self, file_path: str) -> Optional[str]:
        """
        Determines whether the accessed file violates DLP policy.
        Supports both Whitelist (Default Deny) and Blacklist modes.
        """
        norm_path = os.path.normpath(file_path)
        norm_path_lower = norm_path.lower()

        # 1. Ignore Windows OS, Program Files, Packages, System Apps, & Fonts
        if norm_path_lower.startswith("c:\\windows") or "\\windows\\" in norm_path_lower:
            return None
        if "c:\\program files" in norm_path_lower or "c:\\program files (x86)" in norm_path_lower:
            return None
        if "\\appdata\\local\\packages\\" in norm_path_lower:
            return None

        # 2. Ignore Telegram's own internal data, databases, lock files & caches
        if "\\tdata" in norm_path_lower:
            return None
        if "telegram desktop" in norm_path_lower or "telegramdesktop" in norm_path_lower:
            return None
        if "telegram downloads" in norm_path_lower or "telegram_downloads" in norm_path_lower:
            return None
        if "\\shadercache" in norm_path_lower:
            return None
        if "\\appdata\\local\\temp\\" in norm_path_lower or "\\appdata\\local\\temp" in norm_path_lower:
            return None
        if "\\appdata\\roaming\\microsoft\\" in norm_path_lower or "\\appdata\\local\\microsoft\\" in norm_path_lower:
            return None

        _, ext = os.path.splitext(norm_path_lower)

        # 3. Ignore Incoming Telegram Downloads & Temp Download files
        # Prevents killing Telegram when an employee receives / downloads files
        if ext in ('.part', '.tdesktop', '.crdownload', '.download', '.tmp'):
            return None

        # Check if file is freshly created by Telegram (Save As download in progress)
        try:
            stat = os.stat(file_path)
            if (time.time() - stat.st_ctime) < 10 and stat.st_size == 0:
                return None
        except Exception:
            pass

        # 4. If file has NO extension (e.g. named pipes, device handles, OS locks):
        # Do NOT kill on whitelist. Only kill if it actually contains 3D binary magic bytes!
        if not ext:
            matched_sig = check_magic_signature(file_path, self.magic_signatures)
            if matched_sig:
                return f"Detected 3D binary signature in extensionless file: {matched_sig}"
            return None

        # 5. Extension Policy Check
        if self.mode == "whitelist":
            if ext not in self.allowed_extensions:
                return f"Extension ({ext}) not in approved corporate whitelist"
        else:
            if ext in self.blocked_extensions:
                return f"Blocked 3D/Archive extension: {ext}"

        # 6. Magic Header check (catches disguised files, e.g. model.fbx -> notes.txt or photo.jpg)
        matched_sig = check_magic_signature(file_path, self.magic_signatures)
        if matched_sig:
            return f"Detected 3D binary signature: {matched_sig}"

        return None

    def handle_violation(self, proc: psutil.Process, file_path: str, reason: str):
        pid = proc.pid
        name = proc.name()
        try:
            exe_path = proc.exe()
        except Exception:
            exe_path = "N/A"
        try:
            username = proc.username()
        except Exception:
            username = os.environ.get("USERNAME", "N/A")

        file_size = 0
        try:
            file_size = os.path.getsize(file_path)
        except Exception:
            pass

        file_hash = calculate_partial_sha256(file_path)

        incident_info = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "event": "DATA_LEAK_PREVENTION_TRIGGER",
            "reason": reason,
            "process": name,
            "pid": pid,
            "exe": exe_path,
            "user": username,
            "host": self.hostname,
            "file": file_path,
            "file_name": os.path.basename(file_path),
            "file_size_bytes": file_size,
            "partial_sha256": file_hash,
            "action_taken": self.action
        }

        # Log event in JSON
        log_msg = f'"event": "DLP_VIOLATION", "process": "{name}", "pid": {pid}, "user": "{username}", "file": "{file_path.replace(chr(92), "/")}", "reason": "{reason}", "action": "{self.action}"'
        self.logger.warning(log_msg)

        # Enqueue for delivery to central management dashboard (with smart offline buffer)
        if self.reporter:
            self.reporter.enqueue(incident_info)

        # Execute enforcement action
        if self.action == "kill":
            try:
                proc.kill()
                self.logger.info(f'"event": "PROCESS_TERMINATED", "pid": {pid}, "process": "{name}"')
            except Exception as e:
                self.logger.error(f'"event": "TERMINATION_FAILED", "pid": {pid}, "error": "{str(e)}"')

        # Notify user on desktop
        if self.show_popup:
            popup_title = "SECURITY POLICY ALERT - UPLOAD BLOCKED"
            popup_msg = (
                f"A security violation was detected.\n\n"
                f"Application: {name} (PID: {pid})\n"
                f"Attempted File: {os.path.basename(file_path)}\n"
                f"Reason: {reason}\n\n"
                f"Company policy prohibits sharing proprietary 3D assets or archives.\n"
                f"The application has been closed and this event has been logged."
            )
            show_alert_popup(popup_title, popup_msg)

    def scan_cycle(self):
        """Scans all running instances of target processes and their open handles."""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pname = proc.info['name']
                if not pname or pname.lower() not in self.target_processes:
                    continue

                # Query open file handles for this target process
                try:
                    open_files = proc.open_files()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    continue

                for f in open_files:
                    violation_reason = self.is_violation(f.path)
                    if violation_reason:
                        self.handle_violation(proc, f.path, violation_reason)
                        # Process was handled/killed, move to next process
                        break

            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
            except Exception as e:
                # Catch unexpected per-process exceptions so watcher doesn't crash
                continue

    def run(self):
        print("=" * 65)
        print("  DLP WATCHDOG SERVICE ACTIVE")
        print(f"  Target Processes: {list(self.target_processes)}")
        print(f"  Blocked 3D Formats: {len(self.blocked_extensions)} extensions")
        print(f"  Action on detection: {self.action.upper()}")
        print(f"  Poll interval: {int(self.poll_interval * 1000)}ms")
        print("=" * 65)
        print("Monitoring... Press Ctrl+C to stop.")

        try:
            while True:
                self.scan_cycle()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\n[INFO] DLP Watchdog stopped by user.")


def run_supervisor():
    """
    Self-Healing Supervisor: Launches the worker and immediately revives it
    the microsecond an employee attempts to click 'End Task' in Task Manager.
    """
    exe = sys.executable if getattr(sys, 'frozen', False) else [sys.executable, os.path.abspath(__file__)]
    my_pid = os.getpid()
    CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0

    while True:
        try:
            if isinstance(exe, list):
                cmd = exe + ["--worker", f"--parent={my_pid}"]
            else:
                cmd = [exe, "--worker", f"--parent={my_pid}"]

            p = subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW)
            # Wait for worker. If killed in Task Manager, wait() returns immediately!
            p.wait()
            # Revive immediately!
            time.sleep(0.1)
        except Exception:
            time.sleep(1)


def watch_and_revive_supervisor(parent_pid: int):
    """
    Worker background thread: Monitors the supervisor process.
    If an employee kills the supervisor in Task Manager, the worker revives it!
    """
    def _watcher():
        try:
            if not parent_pid or parent_pid <= 0:
                return
            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x00100000
            hParent = kernel32.OpenProcess(SYNCHRONIZE, False, parent_pid)
            if hParent and hParent != 0 and hParent != -1:
                # Blocks until supervisor is terminated
                wait_res = kernel32.WaitForSingleObject(hParent, 0xFFFFFFFF)
                kernel32.CloseHandle(hParent)
                if wait_res == 0:  # WAIT_OBJECT_0: Supervisor actually terminated!
                    exe = sys.executable if getattr(sys, 'frozen', False) else [sys.executable, os.path.abspath(__file__)]
                    CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
                    if isinstance(exe, list):
                        subprocess.Popen(exe, creationflags=CREATE_NO_WINDOW)
                    else:
                        subprocess.Popen([exe], creationflags=CREATE_NO_WINDOW)
        except Exception:
            pass

    t = threading.Thread(target=_watcher, daemon=True)
    t.start()


if __name__ == "__main__":
    # Check if launched as worker or supervisor
    is_worker = "--worker" in sys.argv
    parent_pid = 0
    for arg in sys.argv:
        if arg.startswith("--parent="):
            try:
                parent_pid = int(arg.split("=")[1])
            except Exception:
                pass

    if not is_worker:
        # Run as Self-Healing Supervisor
        run_supervisor()
    else:
        # Run as DLP Monitoring Worker
        if parent_pid > 0:
            watch_and_revive_supervisor(parent_pid)

        cfg = load_config()
        watchdog = DLPWatchdog(cfg)
        watchdog.run()

