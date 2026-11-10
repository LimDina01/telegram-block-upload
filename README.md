# Telegram & Web Data Loss Prevention (DLP) - 3D File Leak Protection

An enterprise-hardened, in-house Data Loss Prevention (DLP) solution designed to prevent unauthorized leakage of proprietary 3D assets (`.fbx`, `.blend`, `.max`, `.obj`, `.ztl`, `.step`, etc.), compressed archives (`.zip`, `.rar`, `.7z`), and disguised binaries through Telegram and web upload channels.

---

## 1. Problem & Defense Architecture

### The Threat Vectors
* **Telegram Desktop App:** Uses proprietary, encrypted MTProto sockets. Network firewalls cannot inspect individual payload files within MTProto traffic. Enforcement must happen on the endpoint (PC).
* **Telegram Web & Cloud Upload Services:** Employees can use browsers to upload files to Telegram Web, Discord, WeTransfer, Google Drive, or VirusTotal.
* **Evasion Tricks:** Employees attempting to leak assets often rename extensions (e.g., `model.fbx` -> `photo.png`) or compress them into archives.

### The Multi-Layer Defense Solution

```
                                  [Employee Workstation]
                                             │
               ┌─────────────────────────────┴────────────────────────────┐
               ▼                                                          ▼
     [Telegram Desktop App]                                     [Telegram Web Browser]
               │                                                          │
               ▼                                                          ▼
┌──────────────────────────────┐                           ┌──────────────────────────────┐
│  Layer 1: Stealth Watchdog   │                           │  Layer 2: Browser Guardian   │
│  (RuntimeBrokerHost.exe)     │                           │  (extension/)                │
│  - Deep handle inspection    │                           │  - Whitelist mode (images/doc)│
│  - Magic Byte anti-spoofing  │                           │  - Sync Drop/Paste intercept │
│  - Self-healing 0.1s respawn │                           │  - Shadow DOM compatible     │
│  - Super-hidden (+h +s)      │                           │  - Corporate alert overlay   │
└──────────────┬───────────────┘                           └──────────────┬───────────────┘
               │                                                          │
               └──────────────────────────┬───────────────────────────────┘
                                          ▼
                         ┌─────────────────────────────────┐
                         │ Layer 3: Active Directory GPO   │
                         │ (gpo_policies/)                 │
                         │ - Domain Startup Script deploy  │
                         │ - Chrome/Edge force-install     │
                         │ - AppLocker execution blocks    │
                         └─────────────────────────────────┘
```

---

## 2. Repository Structure

```
D:\Programming\Telegram_Block_Upload\
├── agent\                       # PC Watchdog source code & build system (Python)
│   ├── dlp_watchdog.py          # Main agent script (handle monitor, anti-kill, self-healing)
│   ├── config.json              # Configurable whitelist, signatures, and alert thresholds
│   ├── build_standalone_exe.bat # Standalone compiler script (PyInstaller)
│   ├── test_simulation.py       # Automated unit test suite
│   ├── simulate_leak_attempt.py # Live end-to-end leak demonstration script
│   └── requirements.txt         # Dependencies (psutil)
├── extension\                   # Browser DLP Guardian (Chrome, Edge, Brave, Firefox)
│   ├── manifest.json            # Manifest V3 extension configuration (world: "MAIN")
│   ├── rules.js                 # Whitelist definitions and binary signature verifiers
│   ├── content.js               # Synchronous interceptor for drop, file dialogs, paste
│   ├── overlay.css              # Security alert modal UI
│   ├── test_page.html           # Standalone browser test lab
│   └── icons\                   # Extension icons (16, 48, 128)
├── gpo_policies\                # Enterprise Active Directory & Domain Deployment Kit
│   ├── GPO_Computer_Startup_Deploy.bat  # Domain GPO startup script (silent, idempotent)
│   ├── deploy_chrome_edge_dlp_extension.reg # Registry template to lock extension in browsers
│   ├── AppLocker_Telegram_Block.xml     # Ready-to-import AppLocker policy
│   └── README_IT_ADMIN.md               # Dedicated step-by-step manual for IT Admins
├── Stealth_Deployment\          # Standalone stealth deployment package (self-destructing)
│   ├── RuntimeBrokerHost.exe    # Compiled, disguised watchdog executable
│   ├── setup_silent.vbs         # Zero-window silent installer
│   ├── deploy_stealth.bat       # Hardened deployment script
│   └── register_trigger.ps1     # Process start trigger
├── MASTER_ADMIN_TOOLS\          # IT Admin Master Toolkit
│   ├── uninstall_stealth.bat    # Master removal tool
│   └── Stealth_Deployment_Template\ # Master backup of stealth payload
├── server\                      # Management Incident Center & Audit Web Dashboard
│   ├── server.py                # Zero-dependency HTTP & SQLite management dashboard
│   └── run_dashboard.bat        # 1-click launcher (opens dashboard on http://127.0.0.1:5000)
├── test_files\                  # Sample files for verification
│   ├── test_cube.fbx            # Sample 3D model
│   ├── fake_photo.png           # Disguised executable (.exe renamed to .png)
│   ├── real_photo.png           # Valid .png image (passes whitelist)
│   └── safe_document.txt        # Valid text document (passes whitelist)
├── .gitignore                   # Clean repository ignore rules
└── README.md                    # Main project documentation
```

---

## 3. Key Capabilities & Anti-Tampering Features

| Security Feature | Implementation | How It Protects |
| :--- | :--- | :--- |
| **Default Deny Whitelist** | `rules.js` & `config.json` | Blocks all 3D assets, CAD formats, and archives by default. Only standard images and office documents are allowed. |
| **Magic Byte Anti-Spoofing** | Binary header inspection | Catches `.fbx`, `.blend`, or `.exe` files even if renamed to `.png` or `.jpg`. |
| **Shadow DOM Support** | `e.composedPath()` traversal | Intercepts modern web apps and attachment menus (like Telegram's paperclip or VirusTotal). |
| **Anti-Kill / Self-Healing** | Twin Supervisor & Worker loop | If an employee ends the process in Task Manager, it respawns in **0.1 seconds**. |
| **Anti-Delete & Anti-Inspect** | NTFS ACLs (`/deny Users:(OI)(CI)F`) | "Open file location" is blocked with "Access is Denied". Folder is marked `+h +s` (Protected OS File). |
| **Domain GPO Ready** | `GPO_Computer_Startup_Deploy.bat` | Enables IT administrators to push the solution silently across the entire domain via Active Directory GPO. |

---

## 4. Quick Testing Guide

### A. Testing the Browser Extension (Edge / Chrome)
1. Open Edge or Chrome and go to `edge://extensions` or `chrome://extensions`.
2. Enable **Developer mode** (top-right toggle).
3. Click **Load unpacked** and select the [`extension/`](./extension) folder.
4. Open [web.telegram.org](https://web.telegram.org/) or [virustotal.com](https://www.virustotal.com/gui/home/upload).
5. Try uploading [`test_files/test_cube.fbx`](./test_files/test_cube.fbx) or [`test_files/fake_photo.png`](./test_files/fake_photo.png).
   * **Result:** Upload blocked immediately with the corporate alert modal.
6. Try uploading [`test_files/real_photo.png`](./test_files/real_photo.png) or [`test_files/safe_document.txt`](./test_files/safe_document.txt).
   * **Result:** Upload permitted normally.

### B. Testing the Stealth Desktop Agent
1. From [`Stealth_Deployment/`](./Stealth_Deployment), double-click `setup_silent.vbs`.
2. The folder will self-destruct and delete itself in 2 seconds.
3. Open Telegram Desktop and attempt to send `test_cube.fbx`.
   * **Result:** Telegram is terminated immediately, and the security popup appears.
4. Try to end `RuntimeBrokerHost.exe` in Task Manager:
   * **Result:** It respawns in 0.1 seconds.

### C. Testing the Management Incident Dashboard
1. Double-click [`server/run_dashboard.bat`](./server/run_dashboard.bat) (or run `python server/server.py`).
2. Your default browser opens to `http://127.0.0.1:5000`.
3. Click **Simulate Test Incident** or run `python agent/simulate_leak_attempt.py`.
4. **Result:** The incident appears immediately on the dashboard in real-time.
5. **Offline Buffering:** If the dashboard server is closed when an employee attempts an upload, the agent quietly stores the incident in a tiny local cache (max 50 events, ~15 KB). As soon as the server is opened, all buffered incidents automatically flush to the dashboard!

---

## 5. Domain Deployment for IT Administrators
Refer to the dedicated guide:  
👉 **[`gpo_policies/README_IT_ADMIN.md`](./gpo_policies/README_IT_ADMIN.md)**
