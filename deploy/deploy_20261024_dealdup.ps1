# Деплой 24.10.2026 (deal dup daily): ежедневная проверка задвоенных товаров в сделках Б24 (06:30 и 15:30). Портал не перезапускается.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'
$out = "$d\deal_dup_daily.py"
Invoke-WebRequest "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/01ef1df2267c8181a8f19b363fd33fb6448e0053/deploy/deal_dup_daily.py" -OutFile "$out.new" -UseBasicParsing
$hh = (Get-FileHash "$out.new" -Algorithm SHA256).Hash.Substring(0,12).ToLower()
if ($hh -ne '4ddee056b5f6') { "СТОП: хэш $hh"; Remove-Item "$out.new"; return }
Move-Item "$out.new" $out -Force
$act = New-ScheduledTaskAction -Execute "$d\.venv\Scripts\python.exe" -Argument "$out" -WorkingDirectory $d
$trg = @((New-ScheduledTaskTrigger -Daily -At 06:30), (New-ScheduledTaskTrigger -Daily -At 15:30))
$set = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 2) -StartWhenAvailable
Register-ScheduledTask -TaskName 'ANESCOM deal dup daily' -Action $act -Trigger $trg -Settings $set -User 'SYSTEM' -RunLevel Highest -Force | Out-Null
"задача: " + (Get-ScheduledTask 'ANESCOM deal dup daily').State + "; следующий запуск: " + (Get-ScheduledTaskInfo 'ANESCOM deal dup daily').NextRunTime
