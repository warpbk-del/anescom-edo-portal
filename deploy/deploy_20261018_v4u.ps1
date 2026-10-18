# Деплой 18.10.2026 (v4u): штамп ЭП с QR внизу страниц документа, новая страница «Отправить на подпись»,
# меню кабинета на телефоне, проверка правдоподобности себестоимости остатков. Ставит pypdf в .venv.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/d8f078b726b720f328eeebeb45bbe1c208d52663"
$files = [ordered]@{
  'app/main.py' = '59694785c257'
  'app/pdfstamp.py' = '4b54b18cbc58'
  'app/dashboards.py' = 'c13a24a4398d'
  'app/static/v3.css' = 'd730eec142ed'
  'app/templates/cabinet_new.html' = '0f58c95edb70'
  'app/templates/cabinet.html' = 'e3d1365a3a8d'
  'app/templates/cabinet_doc.html' = 'cf1dbeec1840'
  'app/templates/dash_base.html' = 'fae490f904f9'
  'app/templates/landing.html' = '67823e11aeab'
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
