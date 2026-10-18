# Деплой 18.10.2026 (v4s): склад и закупки раздельно, Excel заказа и перемещения, отчёты PDF/Excel всех вкладок,
# ABC материалов, ФИО с казахскими буквами, новый логотип, дебиторка в чат «ANESCOM // DEBT» (пятница 19:00).
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/c9d0e3f9ab98f4953c2c5bddb37db9591d3d1fb3"
$files = [ordered]@{
  'app/main.py' = '324ed446704e'
  'app/access.py' = '5d47c4eec999'
  'app/dashboards.py' = '6577f92875a1'
  'app/reports.py' = '62c013656c07'
  'app/xlsx_out.py' = 'a5837e33592c'
  'app/debtweek.py' = '059aee4c2721'
  'app/templates/dash.html' = '303675a30155'
  'app/templates/dash_stock.html' = 'a991fc6a685a'
  'app/templates/dash_base.html' = 'ee91ba252ed3'
  'app/templates/dash_acc.html' = '5a641d8a6d08'
  'app/templates/report.html' = 'e7ac5422f992'
  'app/templates/cabinet.html' = '256c15d8a6b4'
  'app/templates/roles.html' = 'a8aaba4e8786'
  'app/templates/cabinet_doc.html' = '6508fb724799'
  'app/templates/landing.html' = '81a52e359141'
  'app/templates/noaccess.html' = '7af7af6aaa65'
  'app/static/icon-192.png' = 'ec873240a486'
  'app/static/icon-512.png' = 'beecdb5980cd'
  'app/static/apple-touch-icon.png' = '47be41e03a71'
  'app/static/mark.png' = '93c044a4a300'
  'requirements.txt' = 'b63d2eb015c7'
}
$expect = @{ 'app\main.py' = 'b8dd05b58578'; 'app\access.py' = '6a06fc310b2c' }
foreach ($k in $expect.Keys) {
  $cur = (Get-FileHash "$d\$k" -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  "server $k : $cur (ожидали $($expect[$k]))"
  if ($cur -ne $expect[$k]) { "СТОП: $k на сервере отличается"; return }
}
$tmp = Join-Path $env:TEMP "edo_v4s_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v4s"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия: $bk"
& "$d\.venv\Scripts\python.exe" -m pip install -q openpyxl==3.1.5 2>$null; "openpyxl: " + (& "$d\.venv\Scripts\python.exe" -c "import openpyxl;print(openpyxl.__version__)")
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"

# дебиторка: скрипт отправки и задача планировщика (пятница 19:00, от SYSTEM)
Invoke-WebRequest "$raw/deploy/debt_send.py" -OutFile "$d\debt_send.py" -UseBasicParsing
$act = New-ScheduledTaskAction -Execute "$d\.venv\Scripts\python.exe" -Argument "$d\debt_send.py" -WorkingDirectory $d
$trg = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Friday -At 19:00
Register-ScheduledTask -TaskName 'ANESCOM debt' -Action $act -Trigger $trg -User 'SYSTEM' -RunLevel Highest -Force | Out-Null
"задача ANESCOM debt: " + (Get-ScheduledTask 'ANESCOM debt').State
