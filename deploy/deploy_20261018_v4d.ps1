# Деплой 18.10.2026: вкладка «Продажи по филиалам» (/dash/branches), общий шаблон дашбордов.
# Запуск в админ-PowerShell на сервере. Скачивает файлы из GitHub по коммиту и сверяет хэши.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$commit = '18ca57e6dfb88977e89d65232f33bdc913c3672c'
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/$commit"
$files = [ordered]@{
  'app/dashboards.py' = '684973efdc31'
  'app/templates/dash_base.html' = 'a9788a69fdc4'
  'app/templates/dash_macros.html' = 'ec048b9be498'
  'app/templates/dash.html' = '9cb7d02eef47'
  'app/templates/dash_branches.html' = '313422e6cc8d'
  'app/static/dash.css' = 'e3369b7cc267'
}
$cur = (Get-FileHash "$d\app\main.py" -Algorithm SHA256).Hash.Substring(0,16).ToLower()
"server main.py: $cur (ожидали 1a32adfaee0ae400)"
if ($cur -ne '1a32adfaee0ae400') { 'СТОП: main.py на сервере отличается от ожидаемого'; return }
$tmp = Join-Path $env:TEMP "edo_v4d_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $h = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($h -ne $files[$f]) { "СТОП: хэш $f = $h, ожидали $($files[$f])"; return }
}
$bk = "$d\backup_${ts}_v4d"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
'портал перезапущен, ждём старта...'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
# проверка (без секретов): кабинет и дашборд со входом
$env:PYTHONIOENCODING = 'utf-8'
Invoke-WebRequest "$raw/deploy/check_v4b.py" -OutFile "$d\check_v4b.py" -UseBasicParsing
& "$d\.venv\Scripts\python.exe" "$d\check_v4b.py" 2>&1 | Select-Object -Last 8
