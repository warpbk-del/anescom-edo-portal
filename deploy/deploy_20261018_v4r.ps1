# Деплой 18.10.2026 (v4r): утренняя сводка в Bitrix24 + задача планировщика «ANESCOM brief» (пн–сб 8:30).
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/03824f47ea8c8973370c2f136fa13e98ac819028"
$files = [ordered]@{
  'app/main.py' = 'b8dd05b58578'
  'app/config.py' = '6eaad4d98577'
  'app/briefing.py' = 'ae88b520d8ff'
}
$expect = @{ 'app\main.py' = 'aa5870636b28'; 'app\config.py' = 'c90de106a770' }
foreach ($k in $expect.Keys) {
  $cur = (Get-FileHash "$d\$k" -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  "server $k : $cur (ожидали $($expect[$k]))"
  if ($cur -ne $expect[$k]) { "СТОП: $k на сервере отличается"; return }
}
$tmp = Join-Path $env:TEMP "edo_v4r_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v4r"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"

# сводка: скрипт отправки и задача планировщика (пн–сб 8:30, от SYSTEM)
Invoke-WebRequest "$raw/deploy/brief_send.py" -OutFile "$d\brief_send.py" -UseBasicParsing
$act = New-ScheduledTaskAction -Execute "$d\.venv\Scripts\python.exe" -Argument "$d\brief_send.py" -WorkingDirectory $d
$trg = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday,Saturday -At 08:30
Register-ScheduledTask -TaskName 'ANESCOM brief' -Action $act -Trigger $trg -User 'SYSTEM' -RunLevel Highest -Force | Out-Null
"задача ANESCOM brief: " + (Get-ScheduledTask 'ANESCOM brief').State
