# Деплой 18.10.2026 (v5g): все вкладки аналитики рядами одной высоты.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/629d1d774f7bf3b3ed7aa1c0cdc6485b50bab9be"
$files = [ordered]@{
  'app/dashboards.py' = '7fae3f78f775'
  'app/static/dash.css' = 'be20a55b9d17'
  'app/templates/dash.html' = '772329f09166'
  'app/templates/dash_acc.html' = 'bd04f660abd6'
  'app/templates/dash_base.html' = 'c8c9bcca5f94'
  'app/templates/dash_branches.html' = '91cbcdd68b69'
  'app/templates/dash_money.html' = 'be88427fc74f'
  'app/templates/dash_prod.html' = 'cd8ee6fe7b49'
  'app/templates/dash_stock.html' = '736dce4dfbef'
}
# код на сервере должен быть версии v5g (иначе — стоп, чтобы не затереть чужие правки)
$expect = @{ 'app\dashboards.py' = '45b8fbcf0395'; 'app\static\dash.css' = '2d8bf5d30aa4'; 'app\templates\dash.html' = '76630896cc19'; 'app\templates\dash_acc.html' = '59aed5c6fc00'; 'app\templates\dash_base.html' = '8acced14345e'; 'app\templates\dash_branches.html' = '3c888d90bdeb'; 'app\templates\dash_money.html' = '591871d0a034'; 'app\templates\dash_prod.html' = '4ab974e58519'; 'app\templates\dash_stock.html' = 'bb9b05e214c4' }
foreach ($k in $expect.Keys) {
  $cur = (Get-FileHash "$d\$k" -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  "server $k : $cur (ожидали $($expect[$k]))"
  if ($cur -ne $expect[$k]) { "СТОП: $k на сервере отличается"; return }
}
$tmp = Join-Path $env:TEMP "edo_v5g_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v5g"; New-Item -ItemType Directory $bk | Out-Null
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
