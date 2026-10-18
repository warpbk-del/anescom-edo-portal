# Деплой 18.10.2026 (v5m): «Производство АВТОКОМП» — собственный выпуск по участкам (м², т, шт); подсказки графика производства без «₸».
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/8673c97a4dc5eda12929ef4610e09ca87e3e77ac"
$files = [ordered]@{
  'app/dashboards.py' = '65ec0a96fff1'
  'app/templates/dash_prod.html' = '33286d831709'
  'app/reports.py' = 'ebf5b8da1da2'
}
# код на сервере должен быть версии v5m (иначе — стоп, чтобы не затереть чужие правки)
$expect = @{ 'app\dashboards.py' = '5bc51fd03ed9'; 'app\templates\dash_prod.html' = 'cd8ee6fe7b49'; 'app\reports.py' = '078290b83686' }
foreach ($k in $expect.Keys) {
  $cur = (Get-FileHash "$d\$k" -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  "server $k : $cur (ожидали $($expect[$k]))"
  if ($cur -ne $expect[$k]) { "СТОП: $k на сервере отличается"; return }
}
$tmp = Join-Path $env:TEMP "edo_v5m_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v5m"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
"Откат: файлы из $bk."
$pw = (Get-Content "$d\config.env" | ? { $_ -match '^EDO_STAFF_PASSWORD=' }) -replace '^EDO_STAFF_PASSWORD=',''
try { $s = New-Object Microsoft.PowerShell.Commands.WebRequestSession; Invoke-WebRequest http://127.0.0.1:8096/cabinet/login -Method Post -Body @{password=$pw} -WebSession $s -UseBasicParsing -TimeoutSec 15 | Out-Null
  foreach ($u in '/dash/prod?p=month','/dash/prod?p=year','/dash/report?tab=prod&p=year&fmt=xlsx') { $r = Invoke-WebRequest "http://127.0.0.1:8096$u" -WebSession $s -UseBasicParsing -TimeoutSec 30; "$u : $($r.StatusCode) " + ($(if ($r.Content -is [string] -and $r.Content -match 'По участкам') {'участки есть'} else {''})) } } catch { "проверка: " + $_.Exception.Message }
