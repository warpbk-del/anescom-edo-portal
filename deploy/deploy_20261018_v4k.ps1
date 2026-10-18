# Деплой 18.10.2026 (v4k): видимость по ролям (app/access.py), «смотреть как», ФИО в 1С для менеджера.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/cfc0eb5706baafb2506abd2a3a80c52792cffa07"
$files = [ordered]@{
  'app/main.py' = 'aa5870636b28'
  'app/dashboards.py' = 'dde0f01504c4'
  'app/b24auth.py' = '5b3af65c8651'
  'app/access.py' = '6a06fc310b2c'
  'app/templates/cabinet.html' = '4eea7c4a619d'
  'app/templates/dash.html' = 'da0b57682fb7'
  'app/templates/dash_base.html' = '7027e9f1e006'
  'app/templates/roles.html' = '61e12b039ddb'
  'app/templates/noaccess.html' = '74be635349ef'
}
$expect = @{ 'app\main.py' = 'e6a1e796a532'; 'app\dashboards.py' = 'e088c820d4c2'; 'app\b24auth.py' = '9705ebded676' }
foreach ($k in $expect.Keys) {
  $cur = (Get-FileHash "$d\$k" -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  "server $k : $cur (ожидали $($expect[$k]))"
  if ($cur -ne $expect[$k]) { "СТОП: $k на сервере отличается"; return }
}
$tmp = Join-Path $env:TEMP "edo_v4k_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v4k"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
