# Деплой 18.10.2026: дашборд — свои компании (АВТОКОМП) отдельно от долгов и переплат клиентов (коммит 974120a).
# Запуск в админ-PowerShell на сервере. Скачивает файлы из GitHub по коммиту и сверяет хэши.
# Список своих компаний — EDO_INTERNAL_CLIENTS в config.env (через запятую), по умолчанию «АВТОКОМП».
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$commit = '974120a512db60d0696aba709be78517605eb911'
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/$commit"
$files = [ordered]@{
  'app/dashboards.py' = 'da1e0589a2f7'
  'app/config.py' = '0b965cf4fbeb'
  'app/templates/dash.html' = 'eb7fedba8f40'
}
# защита: на сервере должны стоять main.py и config.py из прошлого деплоя (v4d)
$cur = (Get-FileHash "$d\app\main.py" -Algorithm SHA256).Hash.Substring(0,16).ToLower()
"server main.py: $cur (ожидали 1a32adfaee0ae400)"
if ($cur -ne '1a32adfaee0ae400') { 'СТОП: main.py на сервере отличается от ожидаемого'; return }
$cur = (Get-FileHash "$d\app\config.py" -Algorithm SHA256).Hash.Substring(0,16).ToLower()
"server config.py: $cur (ожидали fab339e8630cd7b4)"
if ($cur -ne 'fab339e8630cd7b4') { 'СТОП: config.py на сервере отличается от ожидаемого (правился вручную?)'; return }
$tmp = Join-Path $env:TEMP "edo_v4e_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $h = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($h -ne $files[$f]) { "СТОП: хэш $f = $h, ожидали $($files[$f])"; return }
}
$bk = "$d\backup_${ts}_v4e"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
'портал перезапущен, ждём старта...'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
# проверка (без секретов): кабинет, дашборд, блок «Свои компании»
$env:PYTHONIOENCODING = 'utf-8'
Invoke-WebRequest "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/main/deploy/check_v4e.py" -OutFile "$d\check_v4e.py" -UseBasicParsing
& "$d\.venv\Scripts\python.exe" "$d\check_v4e.py" 2>&1 | Select-Object -Last 8
# откат: скопировать файлы из $bk обратно в app\ и перезапустить задачу «ANESCOM EDO»
