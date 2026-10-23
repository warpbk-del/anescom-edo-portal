# Деплой 23.10.2026 (contactsync i): ежедневная проверка сделок Б24 по 1С (05:00 и 14:30). Портал не перезапускается.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'
$out = "$d\contactsync_daily.py"
Invoke-WebRequest "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/230292aecf1378c8b74e17f33eb4922438a09621/deploy/contactsync_daily.py" -OutFile "$out.new" -UseBasicParsing
$hh = (Get-FileHash "$out.new" -Algorithm SHA256).Hash.Substring(0,12).ToLower()
if ($hh -ne '713cb82d682c') { "СТОП: хэш $hh"; Remove-Item "$out.new"; return }
Move-Item "$out.new" $out -Force
$act = New-ScheduledTaskAction -Execute "$d\.venv\Scripts\python.exe" -Argument "$out" -WorkingDirectory $d
$trg = @((New-ScheduledTaskTrigger -Daily -At 05:00), (New-ScheduledTaskTrigger -Daily -At 14:30))
$set = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 5) -StartWhenAvailable
Register-ScheduledTask -TaskName 'ANESCOM contactsync daily' -Action $act -Trigger $trg -Settings $set -User 'SYSTEM' -RunLevel Highest -Force | Out-Null
"задача: " + (Get-ScheduledTask 'ANESCOM contactsync daily').State + "; следующий запуск: " + (Get-ScheduledTaskInfo 'ANESCOM contactsync daily').NextRunTime
