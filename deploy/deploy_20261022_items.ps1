# Деплой 22.10.2026 (items): вкладка «Товары и группы» — отчёт по товару / группе / бренду / поставщику, PDF и Excel;
# приём новых видов выгрузки 1С (purchases, cost_month) и скидок в продажах. config.env не меняется.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/8bc842d10921fd7cfffbd39472342cf67845d468"
$files = [ordered]@{
  'app/analytics.py' = 'f315af8bd08f'
  'app/dashboards.py' = '5b5bbc40e48a'
  'app/main.py' = '8ce74017c965'
  'app/itemrep.py' = '3fd436a98d70'
  'app/templates/dash_items.html' = 'afb68583aefa'
}
$tmp = Join-Path $env:TEMP "edo_items_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_items"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
Copy-Item "$d\data\analytics.sqlite3" "$bk\analytics.sqlite3"
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены ($($files.Count)), резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
if (-not $ok) { "ОТКАТ: health не прошёл"; foreach ($f in $files.Keys) { $b = Join-Path $bk ($f -replace '/', '_'); $dst = Join-Path $d ($f -replace '/', '\'); if (Test-Path $b) { Copy-Item $b $dst -Force } else { Remove-Item $dst -ea 0 } }; Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'; return }
$pw = (Get-Content "$d\config.env" | ? { $_ -match '^EDO_STAFF_PASSWORD=' }) -replace '^EDO_STAFF_PASSWORD=',''
$s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
try { Invoke-WebRequest http://127.0.0.1:8096/cabinet/login -Method Post -Body @{password=$pw} -WebSession $s -UseBasicParsing -MaximumRedirection 0 -ea 0 | Out-Null } catch {}
foreach ($u in '/health', '/dash/items', '/dash/items?mode=name&q=GEZE', '/dash/items.pdf?mode=name&q=GEZE', '/dash/items.xlsx?mode=name&q=GEZE', '/dash') {
  try { $r = Invoke-WebRequest "http://127.0.0.1:8096$u" -WebSession $s -UseBasicParsing -TimeoutSec 90; "$u : $($r.StatusCode) $($r.RawContentLength)" } catch { "$u : ОШИБКА $($_.Exception.Message)" }
}
"Откат: файлы из $bk."
