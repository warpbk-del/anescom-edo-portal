# Деплой 18.10.2026 (v4i): b24auth.py — OAuth-ответ Bitrix24 на /b24/app.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/324967843502b929dd30400e48f9c3869518c346"
$cur = (Get-FileHash "$d\app\b24auth.py" -Algorithm SHA256).Hash.Substring(0,12).ToLower()
"server b24auth.py: $cur (ожидали a39c263ebc0b)"
if ($cur -ne 'a39c263ebc0b') { 'СТОП: b24auth.py на сервере отличается от ожидаемого'; return }
$tmp = Join-Path $env:TEMP "edo_v4i_$ts.py"
Invoke-WebRequest "$raw/app/b24auth.py" -OutFile $tmp -UseBasicParsing
$h = (Get-FileHash $tmp -Algorithm SHA256).Hash.Substring(0,12).ToLower()
if ($h -ne '2788b9a2d7e5') { "СТОП: хэш $h"; return }
Copy-Item "$d\app\b24auth.py" "$d\app\b24auth.py.bak_${ts}_v4i"
Copy-Item $tmp "$d\app\b24auth.py" -Force; Remove-Item $tmp
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok (копия app\b24auth.py.bak_${ts}_v4i)"
