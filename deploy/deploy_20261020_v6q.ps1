# Деплой v6q 20.10.2026: кадровые документы — в боевую (KADR_NOTIFY_MODE=live), З-2 без изменений
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/75bcd095c44fc9c887c4e344e0c810c5bbc27e8d"
$files = [ordered]@{
  'app/config.py' = '984a3b43f172'
  'app/workflow.py' = 'ea15baa5d010'
}
$tmp = Join-Path $env:TEMP "edo_v6q_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v6q"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
Copy-Item "$d\config.env" "$bk\config.env"
$utf8 = New-Object System.Text.UTF8Encoding($false)
$ce = [IO.File]::ReadAllText("$d\config.env").TrimStart([char]0xFEFF)
if ($ce -match '(?m)^KADR_NOTIFY_MODE=') { $ce = [regex]::Replace($ce, '(?m)^KADR_NOTIFY_MODE=.*$', 'KADR_NOTIFY_MODE=live') }
else { if (-not $ce.EndsWith("`n")) { $ce += "`r`n" }; $ce += "KADR_NOTIFY_MODE=live`r`n" }
[IO.File]::WriteAllText("$d\config.env", $ce, $utf8)
(Get-Content "$d\config.env" | ? { $_ -match '^(SIGN|KADR)_NOTIFY_MODE=' })
"файлы обновлены ($($files.Count)), резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
if (-not $ok) { "ОТКАТ: health не прошёл"; foreach ($f in $files.Keys) { $b = Join-Path $bk ($f -replace '/', '_'); $dst = Join-Path $d ($f -replace '/', '\'); if (Test-Path $b) { Copy-Item $b $dst -Force } else { Remove-Item $dst -ea 0 } }; Copy-Item "$bk\config.env" "$d\config.env" -Force; Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'; return }
$pw = (Get-Content "$d\config.env" | ? { $_ -match '^EDO_STAFF_PASSWORD=' }) -replace '^EDO_STAFF_PASSWORD=',''
$s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
try { Invoke-WebRequest http://127.0.0.1:8096/cabinet/login -Method Post -Body @{password=$pw} -WebSession $s -UseBasicParsing -MaximumRedirection 0 -ea 0 | Out-Null } catch {}
foreach ($u in '/health') {
  try { $r = Invoke-WebRequest "http://127.0.0.1:8096$u" -WebSession $s -UseBasicParsing -TimeoutSec 90; "$u : $($r.StatusCode) $($r.RawContentLength)" } catch { "$u : ОШИБКА $($_.Exception.Message)" }
}
"Откат: файлы из $bk."
# самопроверка /api/kadr на временной базе
$ErrorActionPreference = 'Continue'
$kt = Join-Path $env:TEMP "kadr_selftest_$ts"; New-Item -ItemType Directory $kt | Out-Null
Invoke-WebRequest "$raw/deploy/kadr_selftest.py" -OutFile "$d\kadr_selftest.py" -UseBasicParsing
$env:EDO_DATA_DIR = $kt; $env:PYTHONIOENCODING = 'utf-8'; $env:KADR_NOTIFY_MODE = 'off'; $env:SIGN_NOTIFY_MODE = 'off'
Push-Location $d; cmd /c ".venv\Scripts\python.exe kadr_selftest.py > kt.log 2>&1"; Get-Content kt.log -Encoding UTF8 | Select-Object -Last 12; Pop-Location
Remove-Item Env:EDO_DATA_DIR, Env:KADR_NOTIFY_MODE, Env:SIGN_NOTIFY_MODE; Remove-Item "$d\kadr_selftest.py","$d\kt.log"; Remove-Item $kt -Recurse -ea 0
