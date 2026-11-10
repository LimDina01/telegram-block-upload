' VBScript to launch the DLP Watchdog completely hidden without a visible console window
Set WshShell = CreateObject("WScript.Shell")
strCurDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "python """ & strCurDir & "\dlp_watchdog.py""", 0, False

