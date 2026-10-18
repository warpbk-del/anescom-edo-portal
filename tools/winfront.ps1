# Вывести окно процесса на передний план (восстановить из свёрнутого): powershell -File winfront.ps1 <PID>
param([int]$Id)
Add-Type @"
using System; using System.Runtime.InteropServices;
public class WinFront { [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h); }
"@
$h = (Get-Process -Id $Id).MainWindowHandle
[WinFront]::ShowWindow($h, 9) | Out-Null
[WinFront]::SetForegroundWindow($h) | Out-Null
