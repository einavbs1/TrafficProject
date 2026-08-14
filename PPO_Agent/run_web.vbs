' Double-click this file to start the FlowGrid PPO web app with no visible
' console window. Your browser opens automatically once the server is
' ready. To stop the server, close it from Task Manager (look for
' "python" / "pythonw"), since there is no window to close here.
Set sh = CreateObject("WScript.Shell")
root = Replace(WScript.ScriptFullName, WScript.ScriptName, "")
sh.CurrentDirectory = root
On Error Resume Next
sh.Run "pythonw """ & root & "comparison_web.py""", 1, False
If Err.Number <> 0 Then
    Err.Clear
    sh.Run "python """ & root & "comparison_web.py""", 1, False
End If
