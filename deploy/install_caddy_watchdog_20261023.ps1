# 23.10.2026: caddy (edo.anescom.kz, bot.anescom.kz) stopped 20.10 23:38, nobody noticed for ~32 h.
# Watchdog: every 5 min, if no caddy process -> start task "ANESCOM caddy". Log: D:\caddy\watchdog.log. Run as admin.
$ErrorActionPreference = 'Stop'
$wd = 'D:\caddy\caddy_watchdog.ps1'
@'
$log = 'D:\caddy\watchdog.log'
if (-not (Get-Process caddy -ErrorAction SilentlyContinue)) {
  Start-ScheduledTask 'ANESCOM caddy'
  Start-Sleep 8
  $ok = [bool](Get-Process caddy -ErrorAction SilentlyContinue)
  Add-Content $log ("{0}  caddy was down -> started, running now: {1}" -f (Get-Date -f 'yyyy-MM-dd HH:mm:ss'), $ok)
}
'@ | Set-Content $wd -Encoding ASCII
$act = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File $wd"
$trg = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
$set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'ANESCOM caddy watchdog' -Action $act -Trigger $trg -Settings $set -User 'SYSTEM' -RunLevel Highest -Force | Out-Null
$t = Get-ScheduledTask 'ANESCOM caddy watchdog'
"task: $($t.TaskName) - $($t.State); caddy running: $([bool](Get-Process caddy -ErrorAction SilentlyContinue))"
