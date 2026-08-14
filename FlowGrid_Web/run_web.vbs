' Double-click this file to start FlowGrid_Web with no visible console
' window: builds the dashboard once (npm run build), then starts its own
' backend, which serves both the built UI and its live data API from one
' process (http://127.0.0.1:8001). Your browser opens automatically once
' ready. Never touches PPO_Agent's separate comparison_web dev tool. Run
' run_web.bat once first if this is a fresh checkout (it also runs
' "npm install"); this script assumes node_modules already exists. To
' stop the server, close it from Task Manager (look for
' "python.exe"/"pythonw.exe"), since there is no window to close here.
Set sh = CreateObject("WScript.Shell")
root = Replace(WScript.ScriptFullName, WScript.ScriptName, "")
sh.CurrentDirectory = root

' Build first and wait for it to finish (window hidden, but this step
' must complete before the server below has anything to serve).
sh.Run "cmd /c npm run build", 0, True

On Error Resume Next
sh.Run "pythonw """ & root & "backend\server.py""", 0, False
If Err.Number <> 0 Then
    Err.Clear
    sh.Run "python """ & root & "backend\server.py""", 0, False
End If
