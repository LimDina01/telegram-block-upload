# Active Directory Domain Administrator Deployment Guide
## Corporate Data Loss Prevention (DLP) - 3D File Leak Protection

This guide is designed for **System Administrators / IT Teams** to deploy the DLP solution across all Windows workstations in an Active Directory Domain or via Microsoft Intune.

---

## 1. Architecture Overview

| Component | Target Environment | Deployment Method | Key Capability |
| :--- | :--- | :--- | :--- |
| **Endpoint Watchdog** (`RuntimeBrokerHost.exe`) | Windows 10/11 Workstations | GPO Startup Script / Intune / SCCM | Real-time file handle monitor. Forcibly terminates unauthorized upload attempts, inspects binary magic bytes, self-heals, and auto-restarts. |
| **Web DLP Extension** (`extension/`) | Google Chrome & Microsoft Edge | GPO `ExtensionInstallForcelist` | Intercepts Web Drag & Drop, File Dialogs, and Clipboard Paste across Telegram Web and file-sharing sites. |
| **AppLocker Policy** (`AppLocker_Telegram_Block.xml`) | Windows Domain Policies | Group Policy AppLocker | Optional: Bans native `Telegram.exe` execution entirely across company endpoints. |

---

## 2. Deploying the PC Watchdog via GPO (Active Directory)

### Step 1: Copy Deployment Files to SYSVOL / Network Share
1. Copy the following files to a network share accessible by `Domain Computers` (Read access), such as `\\domain.local\netlogon\CorporateDLP\` or directly into the GPO's Machine Startup folder:
   * `RuntimeBrokerHost.exe` (from `Stealth_Deployment/` or `agent/dist/`)
   * `GPO_Computer_Startup_Deploy.bat` (from `gpo_policies/`)

### Step 2: Configure Group Policy Object (GPO)
1. Open **Group Policy Management Console** (`gpmc.msc`) on your Domain Controller.
2. Create or edit a GPO linked to the Organizational Unit (OU) containing the target workstations (e.g., `OU=3D_Artists,OU=Workstations,DC=company,DC=local`).
3. Navigate to:  
   `Computer Configuration -> Policies -> Windows Settings -> Scripts (Startup/Shutdown) -> Startup`
4. Double-click **Startup**, click **Add...**, and select:  
   `GPO_Computer_Startup_Deploy.bat`
5. Click **OK** and apply the GPO.

### What happens on the client machines:
* At every workstation boot, the script runs silently under **`NT AUTHORITY\SYSTEM`**.
* It installs the binary to `C:\ProgramData\Microsoft\Crypto\SystemBroker\RuntimeBrokerHost.exe`.
* Applies **`+h +s`** attributes (Super-Hidden Protected OS file) and locks NTFS permissions so standard users cannot delete, rename, or inspect it.
* Registers a self-healing 1-minute heartbeat task.
* **Idempotent:** If already installed and running, it completes in ~0.05 seconds with zero boot delay.

---

## 3. Deploying the Browser Extension via GPO (Chrome & Edge)

To deploy the DLP extension silently to all users so they **cannot disable or remove it**:

### Method A: Microsoft Edge via GPO
1. In `gpmc.msc`, navigate to:  
   `Computer Configuration -> Administrative Templates -> Microsoft Edge -> Extensions`
2. Enable **"Configure the list of force-installed apps and extensions"** (`ExtensionInstallForcelist`).
3. Add the Extension ID and update URL (or packed `.crx` path).
4. Recommended: Enable **"InPrivate mode availability"** = *Disabled* (prevents incognito bypass).
5. Recommended: Enable **"Control where developer tools can be used"** = *Disabled*.

### Method B: Google Chrome via GPO
1. Navigate to:  
   `Computer Configuration -> Administrative Templates -> Google Chrome -> Extensions`
2. Enable **"Configure the list of force-installed apps and extensions"** (`ExtensionInstallForcelist`).
3. Recommended: Set **"Incognito mode availability"** = *Disabled*.

*(See [`deploy_chrome_edge_dlp_extension.reg`](./deploy_chrome_edge_dlp_extension.reg) for the exact registry values).*

---

## 4. Optional: Banning Native Telegram via AppLocker

If your company policy mandates that employees should only use approved corporate messengers (Slack, Teams, Mattermost):

1. In `gpmc.msc`, navigate to:  
   `Computer Configuration -> Policies -> Windows Settings -> Security Settings -> Application Control Policies -> AppLocker`
2. Right-click **Executable Rules** -> **Import Policy...**
3. Select [`AppLocker_Telegram_Block.xml`](./AppLocker_Telegram_Block.xml).
4. Ensure the **Application Identity** service (`AppIDSvc`) is set to Automatic on client PCs.
5. Clients will now receive an OS-level block if they attempt to launch `Telegram.exe` from any directory or USB drive.

---

## 5. Centralized Audit Logs & Incident Response

When an employee attempts to upload a 3D asset or unapproved file, the event is recorded locally in:  
`C:\ProgramData\Microsoft\Crypto\SystemBroker\dlp_violations.log`

### Log Format (Structured JSON):
```json
{
  "timestamp": "2026-11-07 09:35:39",
  "level": "WARNING",
  "event": "DLP_VIOLATION",
  "process": "Telegram.exe",
  "pid": 23168,
  "user": "DOMAIN\\artist.name",
  "file": "D:/Projects/Confidential_Model.fbx",
  "reason": "Extension (.fbx) not in approved corporate whitelist",
  "action": "kill"
}
```

### SIEM Ingestion (Splunk, Elastic, Sentinel):
* You can configure your central log forwarder (Winlogbeat, Splunk Universal Forwarder, or Azure Monitor Agent) to ingest `C:\ProgramData\Microsoft\Crypto\SystemBroker\dlp_violations.log`.

---

## 6. Uninstallation & Removal (IT Admins Only)

To remove the guard from a single workstation or via domain script:
* Run [`uninstall_stealth.bat`](../MASTER_ADMIN_TOOLS/uninstall_stealth.bat) as Administrator.
* Or deploy a GPO startup script containing:
  ```bat
  schtasks /delete /tn "Microsoft\Windows\Runtime\SystemBrokerHost" /f >nul 2>&1
  schtasks /delete /tn "Microsoft\Windows\Runtime\SystemBrokerHost_Heartbeat" /f >nul 2>&1
  taskkill /F /IM "RuntimeBrokerHost.exe" >nul 2>&1
  icacls "%ProgramData%\Microsoft\Crypto\SystemBroker" /remove:d Users >nul 2>&1
  rmdir /S /Q "%ProgramData%\Microsoft\Crypto\SystemBroker" >nul 2>&1
  ```

