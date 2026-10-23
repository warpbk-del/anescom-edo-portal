# 23.10.2026: caddy (edo.anescom.kz, bot.anescom.kz) остановился 20.10 23:38 и ~32 ч никто не заметил.
# Ставим присмотр: каждые 5 минут, если процесса caddy нет — запускаем задачу «ANESCOM caddy».
# Журнал: D:\caddy\watchdog.log. Запускать из PowerShell от администратора.
$ErrorActionPreference = 'Stop'
$wd = 'D:\caddy\caddy_watchdog.ps1'
@'
$log = 'D:\caddy\watchdog.log'
if (-not (Get-Process caddy -ErrorAction SilentlyContinue)) {
  Start-ScheduledTask 'ANESCOM caddy'
  Start-Sleep 8
  $ok = [bool](Get-Process caddy -ErrorAction SilentlyContinue)
  Add-Content $log ("{0}  caddy не работал → запущен, сейчас работает: {1}" -f (Get-Date -f 'yyyy-MM-dd HH:mm:ss'), $ok)
}
'@ | Set-Content $wd -Encoding UTF8
$act = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File $wd"
$trg = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
$set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'ANESCOM caddy watchdog' -Action $act -Trigger $trg -Settings $set -User 'SYSTEM' -RunLevel Highest -Force | Out-Null
$t = Get-ScheduledTask 'ANESCOM caddy watchdog'
"задача: $($t.TaskName) — $($t.State); caddy сейчас: $([bool](Get-Process caddy -ErrorAction SilentlyContinue))"
