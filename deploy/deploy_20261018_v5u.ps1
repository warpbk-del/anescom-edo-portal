# Деплой v5u: вход по номеру+паролю, отдельные приложения
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/ca80b2293caf58a3ef6f70451f020f53407bdb6e"
$files = [ordered]@{
  'app/phonelogin.py' = '51ead2e9ca1b'
  'app/clientcab.py' = 'bb1e4459c164'
  'app/main.py' = 'be88f9ab090d'
  'app/helppages.py' = '9737538d95e1'
  'app/templates/login.html' = '47bca4e40647'
  'app/templates/my_login.html' = '9cfba27c308d'
  'app/templates/my_head.html' = '27c8aeef4d34'
  'app/templates/my_admin.html' = '858c543e3b34'
  'app/templates/landing.html' = '1355f7bc650d'
  'app/static/icon-client-192.png' = '1d96da818a6f'
  'app/static/icon-client-512.png' = '455acfde081f'
  'app/static/apple-touch-icon-client.png' = 'adbe503d457e'
}
$tmp = Join-Path $env:TEMP "edo_v5u_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v5u"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
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
foreach ($u in '/','/cabinet','/my','/my/manifest.webmanifest','/manifest.webmanifest','/help/manager','/static/icon-client-192.png') {
  try { $r = Invoke-WebRequest "http://127.0.0.1:8096$u" -WebSession $s -UseBasicParsing -TimeoutSec 90; "$u : $($r.StatusCode) $($r.RawContentLength)" } catch { "$u : ОШИБКА $($_.Exception.Message)" }
}
"Откат: файлы из $bk."
