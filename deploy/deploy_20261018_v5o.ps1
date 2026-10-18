# Деплой 18.10.2026 (v5o): кабинет водителя /driver, инструкции /help, проще подписание клиенту (код в ссылке),
# склад Актобе — только Гульфара, Саламат — склады АВТОКОМП, кнопки прошлых лет, «История по годам».
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/36fac71be7891de9d529a692ebfcf7f6be6fb8b7"
$files = [ordered]@{
  'app/dashboards.py' = '417f3f33f13a'
  'app/templates/dash_history.html' = '2920e79da453'
  'app/reports.py' = '526ca56c0ee9'
  'app/config.py' = '349277c33433'
  'app/access.py' = '05b868822fd0'
  'app/main.py' = '822d17f3e5c6'
  'app/workflow.py' = '43d4769ce287'
  'app/notify.py' = 'c78139764f15'
  'app/templates/sign.html' = 'b87b7e36888c'
  'app/driver.py' = 'ad99aea123ec'
  'app/helppages.py' = '417f381f5867'
  'app/templates/driver.html' = '88b13450eeae'
  'app/templates/help.html' = '3924778ceec7'
  'app/templates/cabinet.html' = '127b01a73617'
  'app/templates/cabinet_new.html' = '887f5fa287a2'
  'app/templates/dash_base.html' = '69ccef5c5576'
  'app/b24auth.py' = 'ac52debb63db'
}
$tmp = Join-Path $env:TEMP "edo_v5o_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v5o"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены ($($files.Count)), резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
if (-not $ok) { "ОТКАТ: health не прошёл — возвращаю файлы"; foreach ($f in $files.Keys) { $b = Join-Path $bk ($f -replace '/', '_'); $dst = Join-Path $d ($f -replace '/', '\'); if (Test-Path $b) { Copy-Item $b $dst -Force } else { Remove-Item $dst -ea 0 } }; Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'; return }
$pw = (Get-Content "$d\config.env" | ? { $_ -match '^EDO_STAFF_PASSWORD=' }) -replace '^EDO_STAFF_PASSWORD=',''
$s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
try { Invoke-WebRequest http://127.0.0.1:8096/cabinet/login -Method Post -Body @{password=$pw} -WebSession $s -UseBasicParsing -MaximumRedirection 0 -ea 0 | Out-Null } catch {}
foreach ($u in '/cabinet','/dash','/dash?p=2025','/dash/history','/dash/stock','/dash/prod','/driver','/help','/help/manager') {
  try { $r = Invoke-WebRequest "http://127.0.0.1:8096$u" -WebSession $s -UseBasicParsing -TimeoutSec 60; "$u : $($r.StatusCode) $($r.RawContentLength)" } catch { "$u : ОШИБКА $($_.Exception.Message)" }
}
"Откат: файлы из $bk."
