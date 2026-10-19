# Деплой v6j: 6п кадровые на подпись: /api/kadr, Мои приказы/договоры
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/a8689df64e4763de3941120806f5cec871b3d7c3"
$files = [ordered]@{
  'app/kadr.py' = '022d24f97c77'
  'app/b24people.py' = 'b8526d7fec1e'
  'app/workflow.py' = '2897fc071eec'
  'app/registry.py' = 'e4ace692786e'
  'app/access.py' = 'b76bd3d2aa1a'
  'app/main.py' = '56d643ae4f32'
  'app/config.py' = 'f0b8dacf0b78'
  'app/templates/cabinet.html' = 'cd25b2578ec3'
}
$tmp = Join-Path $env:TEMP "edo_v6j_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v6j"; New-Item -ItemType Directory $bk | Out-Null
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
foreach ($u in '/health','/cabinet?cat=kadr') {
  try { $r = Invoke-WebRequest "http://127.0.0.1:8096$u" -WebSession $s -UseBasicParsing -TimeoutSec 90; "$u : $($r.StatusCode) $($r.RawContentLength)" } catch { "$u : ОШИБКА $($_.Exception.Message)" }
}
"Откат: файлы из $bk."
# самопроверка /api/kadr на временной базе (Bitrix24 и WhatsApp подменены)
$kt = Join-Path $env:TEMP "kadr_selftest_$ts"; New-Item -ItemType Directory $kt | Out-Null
Invoke-WebRequest "$raw/deploy/kadr_selftest.py" -OutFile "$d\kadr_selftest.py" -UseBasicParsing
$env:EDO_DATA_DIR = $kt; $env:PYTHONIOENCODING = 'utf-8'; [Console]::OutputEncoding = [Text.Encoding]::UTF8
Push-Location $d; & "$d\.venv\Scripts\python.exe" kadr_selftest.py 2>&1 | Select-Object -Last 12; Pop-Location
Remove-Item Env:EDO_DATA_DIR; Remove-Item "$d\kadr_selftest.py"; Remove-Item $kt -Recurse -ea 0
