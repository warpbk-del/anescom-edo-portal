"""Сборка скрипта деплоя: python tools/mkdeploy.py <версия> "<описание>" "<url1,url2>" file1 file2 ...
Коммит берётся из HEAD (файлы должны быть уже закоммичены и запушены)."""
import hashlib, subprocess, sys
ver, desc, urls, files = sys.argv[1], sys.argv[2], sys.argv[3].split(","), sys.argv[4:]
c = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
lines = "\n".join(f"  '{f}' = '{hashlib.sha256(open(f,'rb').read()).hexdigest()[:12]}'" for f in files)
U = ",".join(f"'{u}'" for u in urls)
src = f"""# Деплой {ver}: {desc}
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/{c}"
$files = [ordered]@{{
{lines}
}}
$tmp = Join-Path $env:TEMP "edo_{ver}_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {{
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) {{ "СТОП: хэш $f = $hh"; return }}
}}
$bk = "$d\\backup_${{ts}}_{ver}"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) {{ $src = Join-Path $d ($f -replace '/', '\\'); if (Test-Path $src) {{ Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) }} }}
foreach ($f in $files.Keys) {{ Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\\')) -Force }}
Remove-Item $tmp -Recurse
"файлы обновлены ($($files.Count)), резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) {{ Start-Sleep 5; try {{ if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) {{ $ok = $true; break }} }} catch {{}} }}
"health: $ok"
if (-not $ok) {{ "ОТКАТ: health не прошёл"; foreach ($f in $files.Keys) {{ $b = Join-Path $bk ($f -replace '/', '_'); $dst = Join-Path $d ($f -replace '/', '\\'); if (Test-Path $b) {{ Copy-Item $b $dst -Force }} else {{ Remove-Item $dst -ea 0 }} }}; Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'; return }}
$pw = (Get-Content "$d\\config.env" | ? {{ $_ -match '^EDO_STAFF_PASSWORD=' }}) -replace '^EDO_STAFF_PASSWORD=',''
$s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
try {{ Invoke-WebRequest http://127.0.0.1:8096/cabinet/login -Method Post -Body @{{password=$pw}} -WebSession $s -UseBasicParsing -MaximumRedirection 0 -ea 0 | Out-Null }} catch {{}}
foreach ($u in {U}) {{
  try {{ $r = Invoke-WebRequest "http://127.0.0.1:8096$u" -WebSession $s -UseBasicParsing -TimeoutSec 90; "$u : $($r.StatusCode) $($r.RawContentLength)" }} catch {{ "$u : ОШИБКА $($_.Exception.Message)" }}
}}
"Откат: файлы из $bk."
"""
open(f"deploy/deploy_20261018_{ver}.ps1", "w", encoding="utf-8-sig").write(src)
print(c)
