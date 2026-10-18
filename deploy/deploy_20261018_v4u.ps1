# Деплой 18.10.2026 (v4u): штамп ЭП с QR внизу страниц документа, новая страница «Отправить на подпись»,
# меню кабинета на телефоне, тексты без «простая подпись»/«WhatsApp», проверка правдоподобности себестоимости остатков. Ставит pypdf в .venv.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/aedd6c6b01ee6aeff6facd157ef810e0f5703128"
$files = [ordered]@{
  'app/main.py' = '59694785c257'
  'app/pdfstamp.py' = 'e9b229a90513'
  'app/pdfcert.py' = 'e5635210ae90'
  'app/dashboards.py' = 'c13a24a4398d'
  'app/static/v3.css' = 'd730eec142ed'
  'app/templates/cabinet_new.html' = '525a7906d2fb'
  'app/templates/cabinet.html' = '4c8f726197da'
  'app/templates/cabinet_doc.html' = '023e8b59e188'
  'app/templates/sign.html' = '17f36efe1e7e'
  'app/templates/dash_base.html' = 'fae490f904f9'
  'app/templates/landing.html' = 'ccdc9e74625f'
  'app/templates/noaccess.html' = '249ed21bc552'
  'app/templates/roles.html' = 'e3940192b96f'
}
# код на сервере должен быть версии v4t (иначе — стоп, чтобы не затереть чужие правки)
$expect = @{ 'app\main.py' = '324ed446704e'; 'app\dashboards.py' = '72cf0b0d7a92' }
foreach ($k in $expect.Keys) {
  $cur = (Get-FileHash "$d\$k" -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  "server $k : $cur (ожидали $($expect[$k]))"
  if ($cur -ne $expect[$k]) { "СТОП: $k на сервере отличается"; return }
}
$py = "$d\.venv\Scripts\python.exe"
& $py -m pip install -q pypdf==5.9.0
& $py -c "import pypdf; print('pypdf', pypdf.__version__)"
if ($LASTEXITCODE -ne 0) { "СТОП: pypdf не установился"; return }
$tmp = Join-Path $env:TEMP "edo_v4u_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v4u"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
"Проверка: откройте документ в кабинете — внизу страниц штамп с QR. Откат: скопировать файлы из $bk."
