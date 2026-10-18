# Деплой 18.10.2026 (v4g): вход сотрудников через Bitrix24 (app/b24auth.py, main.py, config.py, login.html).
# В config.env дописываются B24_CLIENT_ID и B24_ADMIN_IDS (если их нет); B24_CLIENT_SECRET вписывает пользователь.
# Запуск в админ-PowerShell на сервере. Скачивает файлы из GitHub по коммиту и сверяет хэши.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$commit = '65ffb728a22bccd9e4749440f55129349fe08447'
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/$commit"
$files = [ordered]@{
  'app/b24auth.py' = '4b7bcbdbe3ef'
  'app/main.py' = '2f02da60c2db'
  'app/config.py' = 'c90de106a770'
  'app/templates/login.html' = '0d7fb6552458'
}
# защита: на сервере должны стоять main.py (v4d) и config.py (v4f)
$cur = (Get-FileHash "$d\app\main.py" -Algorithm SHA256).Hash.Substring(0,16).ToLower()
"server main.py: $cur (ожидали 1a32adfaee0ae400)"
if ($cur -ne '1a32adfaee0ae400') { 'СТОП: main.py на сервере отличается от ожидаемого'; return }
$cur = (Get-FileHash "$d\app\config.py" -Algorithm SHA256).Hash.Substring(0,16).ToLower()
"server config.py: $cur (ожидали 0b965cf4fbebf1c2)"
if ($cur -ne '0b965cf4fbebf1c2') { 'СТОП: config.py на сервере отличается от ожидаемого (правился вручную?)'; return }
$tmp = Join-Path $env:TEMP "edo_v4g_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $h = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($h -ne $files[$f]) { "СТОП: хэш $f = $h, ожидали $($files[$f])"; return }
}
$bk = "$d\backup_${ts}_v4g"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия: $bk"
$envf = "$d\config.env"; $envtxt = [IO.File]::ReadAllText($envf)
Copy-Item $envf "$d\config.env.bak_${ts}_v4g"
$add = @()
if ($envtxt -notmatch '(?m)^B24_CLIENT_ID=') { $add += 'B24_CLIENT_ID=local.6ad4902a8bd613.41034333' }
if ($envtxt -notmatch '(?m)^B24_ADMIN_IDS=') { $add += 'B24_ADMIN_IDS=355' }
if ($envtxt -notmatch '(?m)^B24_CLIENT_SECRET=') { $add += 'B24_CLIENT_SECRET=' }
if ($add.Count) { [IO.File]::AppendAllText($envf, ("`r`n" + ($add -join "`r`n") + "`r`n"), (New-Object Text.UTF8Encoding $false)); "config.env: добавлено $($add.Count) строк(и)" }
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
'портал перезапущен, ждём старта...'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
# проверка (без секретов): кабинет, дашборд, блок «Свои компании»
$env:PYTHONIOENCODING = 'utf-8'
Invoke-WebRequest "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/main/deploy/check_v4g.py" -OutFile "$d\check_v4g.py" -UseBasicParsing
& "$d\.venv\Scripts\python.exe" "$d\check_v4g.py" 2>&1 | Select-Object -Last 8
# откат: скопировать файлы из $bk обратно в app\ и перезапустить задачу «ANESCOM EDO»
