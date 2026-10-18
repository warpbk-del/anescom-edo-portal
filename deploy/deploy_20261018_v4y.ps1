# Деплой 18.10.2026 (v4y): аналитика — углы кнопок/фильтров менее круглые (6/4 px), кнопки «Отчёт PDF/Excel» читаемые на тёмном фоне; ГРИНТЕ — своя компания (EDO_INTERNAL_CLIENTS).
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/e97f4c840686070a0c1b2954d36b20fc8231d01e"
$files = [ordered]@{
  'app/static/dash.css' = '35d1d71c8de3'
  'app/templates/dash_base.html' = '8df05514f3aa'
  'app/config.py' = '9e8d89ce46d3'
}
# код на сервере должен быть версии v4y (иначе — стоп, чтобы не затереть чужие правки)
$expect = @{ 'app\static\dash.css' = 'e3369b7cc267'; 'app\templates\dash_base.html' = '975f799ac5ae'; 'app\config.py' = 'd6604acb3957' }
foreach ($k in $expect.Keys) {
  $cur = (Get-FileHash "$d\$k" -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  "server $k : $cur (ожидали $($expect[$k]))"
  if ($cur -ne $expect[$k]) { "СТОП: $k на сервере отличается"; return }
}
$tmp = Join-Path $env:TEMP "edo_v4y_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v4y"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия: $bk"
# свои компании в config.env (если строка задана — она важнее значения в коде)
$envf = "$d\config.env"; $lines = [IO.File]::ReadAllLines($envf, [Text.Encoding]::UTF8)
$i = [Array]::FindIndex($lines, [Predicate[string]]{ param($l) $l -match '^\s*EDO_INTERNAL_CLIENTS\s*=' })
if ($i -ge 0) { if ($lines[$i] -notmatch 'ГРИНТЕ') { Copy-Item $envf "$bk\config.env"; $lines[$i] = $lines[$i].TrimEnd() + ',ГРИНТЕ,GREENTE'; [IO.File]::WriteAllLines($envf, $lines, (New-Object Text.UTF8Encoding $false)) } }
"EDO_INTERNAL_CLIENTS: " + $(if ($i -ge 0) { $lines[$i] } else { 'нет в config.env — берётся из кода' })
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
"Откат: файлы из $bk."
try { "static/dash.css: " + (Invoke-WebRequest http://127.0.0.1:8096/static/dash.css -UseBasicParsing -TimeoutSec 10).StatusCode } catch { "static/dash.css: " + $_.Exception.Message }
