# Деплой 23.10.2026 (contactsync d): снимок b24ids (регистр идентификаторов коннектора) и план его чистки.
# config.env не меняется (DEAL_SYNC_MODE=live уже задан 23.10 08:29).
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/f55abac4d43dca129186f982cfe9b73017e9bd4c"
$files = [ordered]@{
  'app/analytics.py' = '0eee6db237d0'
  'app/contactsync.py' = '1475d7d2f6d9'
}
$tmp = Join-Path $env:TEMP "edo_contactsynce_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_contactsynce"; New-Item -ItemType Directory $bk | Out-Null
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
$tk = (Get-Content "$d\config.env" | ? { $_ -match '^EDO_API_TOKEN=' }) -replace '^EDO_API_TOKEN=',''
$h = @{Authorization = "Bearer $tk"}
try { $r = Invoke-WebRequest http://127.0.0.1:8096/api/contactsync/last -Headers $h -UseBasicParsing -TimeoutSec 30; "contactsync/last : $($r.StatusCode) $($r.Content)" } catch { "contactsync/last : ОШИБКА $($_.Exception.Message)" }
try { $r = Invoke-WebRequest http://127.0.0.1:8096/dash -UseBasicParsing -TimeoutSec 30 -MaximumRedirection 0 -ea 0; "/dash : $($r.StatusCode)" } catch { "/dash : $($_.Exception.Message)" }
"Откат: файлы из $bk."
