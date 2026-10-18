# Деплой v5x: долги на 31.12 выбранного года
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/9a4df3190124b1fc483a17e85f687c232757452d"
$files = [ordered]@{
  'app/dashboards.py' = 'f56bfc1ba16d'
  'app/templates/dash.html' = 'a1a8f513fa48'
  'app/templates/dash_acc.html' = 'f88b3207ac64'
}
$tmp = Join-Path $env:TEMP "edo_v5x_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v5x"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены ($($files.Count)), резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
if (-not $ok) { "ОТКАТ: health не прошёл"; foreach ($f in $files.Keys) { $b = Join-Path $bk ($f -replace '/', '_'); $dst = Join-Path $d ($f -replace '/', '\'); if (Test-Path $b) { Copy-Item $b $dst -Force } else { Remove-Item $dst -ea 0 } }; Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'; return }
$py = if (Test-Path "$d\.venv\Scripts\python.exe") { "$d\.venv\Scripts\python.exe" } else { 'python' }
Push-Location $d
& $py -c "import time; from app import dashboards as D; t=time.time(); D.build('month','','',''); a=time.time()-t; t=time.time(); D.build('month','','',''); print('build month: %.1f s, повтор из кэша: %.2f s' % (a, time.time()-t)); t=time.time(); D.build('2023','','',''); print('2023 долги:', round(D.build('2023','','','').get('debt',0)/1e6), D.build('2023','','','').get('debt_asof')); print('build year: %.1f s' % (time.time()-t))"
Pop-Location
"Откат: файлы из $bk."
