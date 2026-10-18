# Деплой 18.10.2026 09:20: версия v3.css в ссылках (сброс кэша браузера), номер 1С в карточке,
# config.py читает config.env с BOM (utf-8-sig).
# Запуск в админ-PowerShell на сервере. Скачивает файлы из GitHub по коммиту и сверяет хэши.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$commit = 'a6f2e3a885a7f85cf3171b04660bd88ee75753e6'
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/$commit"
$files = [ordered]@{
  'app/main.py'                    = '7a999138382e'
  'app/config.py'                  = 'b42d1f8ec2ad'
  'app/templates/cabinet.html'     = '63ecee679229'
  'app/templates/cabinet_doc.html' = 'ff59483406e5'
  'app/templates/landing.html'     = '608e4c8c799e'
}
$cur = (Get-FileHash "$d\app\main.py" -Algorithm SHA256).Hash.Substring(0,16).ToLower()
"server main.py: $cur (ожидали 4aa48cd5572d1052)"
if ($cur -ne '4aa48cd5572d1052') { 'СТОП: main.py на сервере отличается от ожидаемого'; return }
$tmp = Join-Path $env:TEMP "edo_v3s2b_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $h = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($h -ne $files[$f]) { "СТОП: хэш $f = $h, ожидали $($files[$f])"; return }
}
$bk = "$d\backup_${ts}_v3s2b"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
'портал перезапущен, ждём старта...'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
# проверка (без секретов)
$env:PYTHONIOENCODING = 'utf-8'
Invoke-WebRequest "$raw/deploy/check_v3s2.py" -OutFile "$d\check_v3s2.py" -UseBasicParsing
& "$d\.venv\Scripts\python.exe" "$d\check_v3s2.py" 2>&1 | Select-Object -Last 14
