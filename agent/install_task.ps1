# PowerShell script to register DLP Watchdog as a Windows Scheduled Task
# Run as Administrator

param(
    [switch]$Uninstall
)

$TaskName = "Corporate_Telegram_3D_DLP_Watchdog"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VbsPath = Join-Path $ScriptDir "run_hidden.vbs"

if ($Uninstall) {
    Write-Host "[*] Removing scheduled task: $TaskName..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "[+] Task removed successfully." -ForegroundColor Green
    exit 0
}

Write-Host "[*] Registering DLP Watchdog scheduled task: $TaskName..." -ForegroundColor Cyan

# Action: launch wscript with the hidden launcher
$Action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$VbsPath`""

# Trigger: at user logon
$Trigger = New-ScheduledTaskTrigger -AtLogOn

# Principal: Run with highest privileges (needed to inspect process handles)
$Principal = New-ScheduledTaskPrincipal -GroupId "BUILTIN\Administrators" -RunLevel Highest

# Settings: Restart on failure, don't stop on battery
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit 0

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force

Write-Host "[+] Successfully registered $TaskName! The watchdog will run silently on logon." -ForegroundColor Green
Write-Host "[+] To start it now immediately, run: Start-ScheduledTask -TaskName `"$TaskName`"" -ForegroundColor Cyan

