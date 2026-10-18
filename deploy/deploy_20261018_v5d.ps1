# Деплой 18.10.2026 (v5d): ровная сетка аналитики — полоса показателей (кольцо + плитки 3×2) на всех вкладках, «Компания» рядами одной высоты.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/88ecac1b3605511446f74666ea381475e48197f1"
$files = [ordered]@{
  'app/dashboards.py' = '655eb5ad0a13'
  'app/static/dash.css' = 'dceca201d6d7'
  'app/templates/dash.html' = 'b3c4384d6623'
  'app/templates/dash_base.html' = 'af9800946372'
}
# код на сервере должен быть версии v5d (иначе — стоп, чтобы не затереть чужие правки)
$expect = @{ 'app\dashboards.py' = '98b62e3f23b9'; 'app\static\dash.css' = '75c03732446c'; 'app\templates\dash.html' = '5e7fb13d2790'; 'app\templates\dash_base.html' = '4cf9b8ee8ee0' }
foreach ($k in $expect.Keys) {
  $cur = (Get-FileHash "$d\$k" -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  "server $k : $cur (ожидали $($expect[$k]))"
  if ($cur -ne $expect[$k]) { "СТОП: $k на сервере отличается"; return }
}
$tmp = Join-Path $env:TEMP "edo_v5d_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v5d"; New-Item -ItemType Directory $bk | Out-Null
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
