# Деплой портала v3, этап 1 (18.10.2026): «Мои задачи», разделы, подразделения.
# Запуск в админ-PowerShell на сервере. Скачивает файлы из GitHub по коммиту и сверяет хэши.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$commit = 'e9de16cb2ad0240264d8f70b4922f43eb0919d69'
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/$commit"
$files = [ordered]@{
  'app/main.py'                = '0d30321c2f09'
  'app/registry.py'            = '24f3f346902c'
  'app/templates/cabinet.html' = 'e6153e0abd13'
  'app/static/v3.css'          = 'f4914c0e2e03'
}
$cur = (Get-FileHash "$d\app\main.py" -Algorithm SHA256).Hash.Substring(0,16).ToLower()
"server main.py: $cur (ожидали e727aca24c3ed1d5)"
if ($cur -ne 'e727aca24c3ed1d5') { 'СТОП: main.py на сервере отличается от ожидаемого'; return }
$tmp = Join-Path $env:TEMP "edo_v3_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $h = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($h -ne $files[$f]) { "СТОП: хэш $f = $h, ожидали $($files[$f])"; return }
}
$bk = "$d\backup_${ts}_v3"; New-Item -ItemType Directory $bk | Out-Null
Copy-Item "$d\app\main.py", "$d\app\templates\cabinet.html" $bk
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
'портал перезапущен, ждём старта...'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
# проверка «Мои задачи» под служебной cookie (без вывода секретов)
$py = "$d\.venv\Scripts\python.exe"
$code = 'import sys; sys.path.insert(0, r"D:\anescom_edo"); from fastapi.testclient import TestClient; from app import main; c = TestClient(main.app); c.cookies.set(main._COOKIE, main._make_cookie()); r = c.get("/cabinet", headers={"host": "edo.anescom.kz"}); print("cabinet", r.status_code, "Мои задачи" in r.text, "v3.css" in r.text); r2 = c.get("/cabinet?view=all&cat=nakl", headers={"host": "edo.anescom.kz"}); print("nakl", r2.status_code)'
& $py -c $code 2>&1 | Select-Object -Last 3
