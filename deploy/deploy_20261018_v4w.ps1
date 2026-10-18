# Деплой 18.10.2026 (v4w): вкладка «Производство АВТОКОМП» /dash/prod (приём prod_in, prod_orders, prod_raw из 1С), отчёт PDF/Excel.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/8e81e83726cc111cffc930d24bae34f7ffccfef4"
$files = [ordered]@{
  'app/analytics.py' = 'f271ba95cb86'
  'app/dashboards.py' = 'ae49c4784848'
  'app/reports.py' = 'b0e085c24114'
  'app/templates/dash_prod.html' = '61b181fee92e'
}
# код на сервере должен быть версии v4v (иначе — стоп, чтобы не затереть чужие правки)
$expect = @{ 'app\analytics.py' = '5af0e0befbe9'; 'app\dashboards.py' = 'c13a24a4398d'; 'app\reports.py' = '62c013656c07' }
foreach ($k in $expect.Keys) {
  $cur = (Get-FileHash "$d\$k" -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  "server $k : $cur (ожидали $($expect[$k]))"
  if ($cur -ne $expect[$k]) { "СТОП: $k на сервере отличается"; return }
}
$tmp = Join-Path $env:TEMP "edo_v4w_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v4w"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
"Проверка: /dash/prod — 200. Откат: файлы из $bk."
try { "dash/prod: " + (Invoke-WebRequest http://127.0.0.1:8096/dash/prod -UseBasicParsing -TimeoutSec 10).StatusCode } catch { "dash/prod: " + $_.Exception.Message }
