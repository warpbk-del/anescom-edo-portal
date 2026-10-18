# Деплой 18.10.2026 (v5j): Склады — ABC каждого склада (товары, группы) и мин/макс остатков по классу; листы в Excel.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/862384eed1aa3725dac22b7a90057422ecfe9a75"
$files = [ordered]@{
  'app/dashboards.py' = '5bc51fd03ed9'
  'app/reports.py' = '078290b83686'
  'app/static/dash.css' = 'e90b9f39162c'
  'app/templates/dash_base.html' = 'd121820a933c'
  'app/templates/dash_stock.html' = 'bd629991ee6c'
}
# код на сервере должен быть версии v5j (иначе — стоп, чтобы не затереть чужие правки)
$expect = @{ 'app\dashboards.py' = '7fae3f78f775'; 'app\reports.py' = 'b0e085c24114'; 'app\static\dash.css' = '20993534cd55'; 'app\templates\dash_base.html' = '9043217fc35f'; 'app\templates\dash_stock.html' = 'eb0f3c322675' }
foreach ($k in $expect.Keys) {
  $cur = (Get-FileHash "$d\$k" -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  "server $k : $cur (ожидали $($expect[$k]))"
  if ($cur -ne $expect[$k]) { "СТОП: $k на сервере отличается"; return }
}
$tmp = Join-Path $env:TEMP "edo_v5j_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v5j"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
"Откат: файлы из $bk."
try { "static/dash.css: " + (Invoke-WebRequest http://127.0.0.1:8096/static/dash.css -UseBasicParsing -TimeoutSec 10).StatusCode } catch { "static/dash.css: " + $_.Exception.Message }
