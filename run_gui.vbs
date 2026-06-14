' Double-click this file to open FlowGrid with no black command window.
Set sh = CreateObject("WScript.Shell")
root = Replace(WScript.ScriptFullName, WScript.ScriptName, "")
sh.CurrentDirectory = root
On Error Resume Next
sh.Run "pythonw """ & root & "flowgrid_gui.py""", 1, False
If Err.Number <> 0 Then
    Err.Clear
    sh.Run "python """ & root & "flowgrid_gui.py""", 1, False
End If
