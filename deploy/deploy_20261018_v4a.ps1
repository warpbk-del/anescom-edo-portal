# Деплой 18.10.2026: портал v4 этап A — приём аналитики из 1С (/api/analytics/*, база data\analytics.sqlite3)
# + название EDO.ANESCOM латиницей (если ещё не поставлено). Только после «ставь» пользователя.
# Запуск в админ-PowerShell на сервере. Скачивает файлы из GitHub по коммиту и сверяет хэши.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$commit = '0af95b2be8e21e16e1a959ef57e0f71f3ef3a77f'
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/$commit"
$files = [ordered]@{
  'app/config.py' = 'fab339e8630c'
  'app/db.py' = '33f58905ad03'
  'app/main.py' = 'cc32faa3838d'
  'app/analytics.py' = '5af0e0befbe9'
  'app/pdfcert.py' = '25ef0f216736'
  'app/static/style.css' = '18c83bbb6ecf'
  'app/static/v3.css' = '06ddf3540189'
  'app/templates/cabinet.html' = '39a6817adebe'
  'app/templates/cabinet_doc.html' = 'd280b43e37f6'
  'app/templates/cabinet_new.html' = 'a127b52c20a8'
  'app/templates/landing.html' = 'f6c41483ad39'
  'app/templates/login.html' = '3e42398f292c'
  'app/templates/sign.html' = 'ef1ddae4eff2'
}
$cur = (Get-FileHash "$d\app\main.py" -Algorithm SHA256).Hash.Substring(0,16).ToLower()
"server main.py: $cur (ожидали 7a999138382e47b2 — до переименования, или e59b06361bb2ac14 — после)"
if ($cur -ne '7a999138382e47b2' -and $cur -ne 'e59b06361bb2ac14') { 'СТОП: main.py на сервере отличается от ожидаемого'; return }
$tmp = Join-Path $env:TEMP "edo_v4a_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $h = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($h -ne $files[$f]) { "СТОП: хэш $f = $h, ожидали $($files[$f])"; return }
}
$bk = "$d\backup_${ts}_v4a"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
'портал перезапущен, ждём старта...'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
# проверка (без секретов): кабинет и приём аналитики
$env:PYTHONIOENCODING = 'utf-8'
Invoke-WebRequest "$raw/deploy/check_v3s2.py" -OutFile "$d\check_v3s2.py" -UseBasicParsing
& "$d\.venv\Scripts\python.exe" "$d\check_v3s2.py" 2>&1 | Select-Object -Last 6
$tok = ((Get-Content "$d\config.env" -Encoding UTF8 | Where-Object { $_ -match '^\s*EDO_API_TOKEN\s*=' }) -replace '^[^=]*=\s*', '').Trim('"', ' ')
$st = Invoke-WebRequest http://127.0.0.1:8096/api/analytics/status -Headers @{Authorization = "Bearer $tok"} -UseBasicParsing
"analytics/status: $($st.StatusCode) $($st.Content.Substring(0, [Math]::Min(200, $st.Content.Length)))"
