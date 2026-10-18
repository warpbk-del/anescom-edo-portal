# Деплой портала v3, этап 2 часть 1 (18.10.2026 утро): карточка документа v3, пропуск шага,
# промежуточный протокол с QR, маршрут З-2 менеджер → клиент → кладовщик, главная с кнопкой входа.
# Запуск в админ-PowerShell на сервере. Скачивает файлы из GitHub по коммиту и сверяет хэши.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$commit = '213ba000f4ace61ccde5a6d53f6069974d7905ff'
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/$commit"
$files = [ordered]@{
  'app/main.py'                    = '4aa48cd5572d'
  'app/workflow.py'                = '78a65ac3af7d'
  'app/registry.py'                = '5a24ee577102'
  'app/z2.py'                      = '7c2654d2aa85'
  'app/pdfcert.py'                 = 'da0f65dcb3e5'
  'app/templates/cabinet_doc.html' = 'c1a1eb3777f3'
  'app/templates/sign.html'        = 'b822c9d38dc0'
  'app/templates/landing.html'     = '396f65d6f9ca'
  'app/static/v3.css'              = '6f9a79fd688b'
}
$cur = (Get-FileHash "$d\app\main.py" -Algorithm SHA256).Hash.Substring(0,16).ToLower()
"server main.py: $cur (ожидали 0d30321c2f097aa1)"
if ($cur -ne '0d30321c2f097aa1') { 'СТОП: main.py на сервере отличается от ожидаемого'; return }
$tmp = Join-Path $env:TEMP "edo_v3s2_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $h = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($h -ne $files[$f]) { "СТОП: хэш $f = $h, ожидали $($files[$f])"; return }
}
$bk = "$d\backup_${ts}_v3s2"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
'портал перезапущен, ждём старта...'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
# проверка: главная, кабинет, карточка; адрес ссылок (без секретов)
$py = "$d\.venv\Scripts\python.exe"
$code = 'import sys; sys.path.insert(0, r"D:\anescom_edo"); from fastapi.testclient import TestClient; from app import main, config, db; c = TestClient(main.app); h = {"host": "edo.anescom.kz"}; print("landing", c.get("/", headers=h).status_code); c.cookies.set(main._COOKIE, main._make_cookie()); print("cabinet", c.get("/cabinet", headers=h).status_code); con = db.conn().__enter__(); r = con.execute("SELECT id FROM documents WHERE workflow=1 ORDER BY created_at DESC LIMIT 1").fetchone(); print("card", c.get("/cabinet/doc/" + r[0], headers=h).status_code if r else "-"); print("PUBLIC_BASE_URL =", config.PUBLIC_BASE_URL)'
& $py -c $code 2>&1 | Select-Object -Last 5
'config.env, строки адреса:'; Select-String -Path "$d\config.env" -Pattern 'EDO_PUBLIC_BASE_URL|EDO_ROOT_PATH' | ForEach-Object { $_.Line }
