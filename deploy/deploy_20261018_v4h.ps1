# Деплой 18.10.2026 (v4h): b24auth.py — OAuth-ответ Bitrix24 на /b24/app.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/02a9084d7f465e740e3dec150c68837778397ea4"
$cur = (Get-FileHash "$d\app\b24auth.py" -Algorithm SHA256).Hash.Substring(0,16).ToLower()
"server b24auth.py: $cur (ожидали 4b7bcbdbe3ef2c45)"
if ($cur -ne '4b7bcbdbe3ef2c45') { 'СТОП: b24auth.py на сервере отличается от ожидаемого'; return }
$tmp = Join-Path $env:TEMP "edo_v4h_$ts.py"
Invoke-WebRequest "$raw/app/b24auth.py" -OutFile $tmp -UseBasicParsing
$h = (Get-FileHash $tmp -Algorithm SHA256).Hash.Substring(0,12).ToLower()
if ($h -ne 'a39c263ebc0b') { "СТОП: хэш $h"; return }
Copy-Item "$d\app\b24auth.py" "$d\app\b24auth.py.bak_${ts}_v4h"
Copy-Item $tmp "$d\app\b24auth.py" -Force; Remove-Item $tmp
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok (копия app\b24auth.py.bak_${ts}_v4h)"
