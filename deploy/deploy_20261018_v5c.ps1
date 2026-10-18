# Деплой 18.10.2026 (v5c): компактный вид на всех вкладках аналитики — график рядом с показателями, без растянутых карточек, прокрутка длинных таблиц, короткие названия филиалов.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/f61a36994d3776631f5e52c56e53c32a541dd007"
$files = [ordered]@{
  'app/dashboards.py' = '98b62e3f23b9'
  'app/static/dash.css' = '75c03732446c'
  'app/templates/dash_acc.html' = '59aed5c6fc00'
  'app/templates/dash_base.html' = '4cf9b8ee8ee0'
  'app/templates/dash_branches.html' = '3c888d90bdeb'
  'app/templates/dash_money.html' = '591871d0a034'
  'app/templates/dash_prod.html' = '4ab974e58519'
  'app/templates/dash_stock.html' = 'bb9b05e214c4'
}
# код на сервере должен быть версии v5c (иначе — стоп, чтобы не затереть чужие правки)
$expect = @{ 'app\dashboards.py' = '4a2275fd9fcf'; 'app\static\dash.css' = '3553db2d292a'; 'app\templates\dash_acc.html' = '5a641d8a6d08'; 'app\templates\dash_base.html' = '78f532231607'; 'app\templates\dash_branches.html' = '313422e6cc8d'; 'app\templates\dash_money.html' = '9b70dc1209e4'; 'app\templates\dash_prod.html' = '61b181fee92e'; 'app\templates\dash_stock.html' = 'a991fc6a685a' }
foreach ($k in $expect.Keys) {
  $cur = (Get-FileHash "$d\$k" -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  "server $k : $cur (ожидали $($expect[$k]))"
  if ($cur -ne $expect[$k]) { "СТОП: $k на сервере отличается"; return }
}
$tmp = Join-Path $env:TEMP "edo_v5c_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v5c"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
"Откат: файлы из $bk."
try { "static/dash.css: " + (Invoke-WebRequest http://127.0.0.1:8096/static/dash.css -UseBasicParsing -TimeoutSec 10).StatusCode } catch { "static/dash.css: " + $_.Exception.Message }
