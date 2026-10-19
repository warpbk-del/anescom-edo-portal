# Деплой v6d: фин. план — АВТОКОМП колонкой «Производство» (6о)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/e974a532c8b64541c06bfdf7f80997837160c0f7"
$files = [ordered]@{
  'app/finplan.py' = '4d5b541efbed'
  'app/templates/dash_finplan.html' = 'a24998ab0810'
  'app/templates/finplan_print.html' = '8d45ae224cea'
}
# 1) скрипты фин. плана → D:\anescom_edo\legacy\py и сборка факта (an_fin_fact) до перезапуска портала
$lp = 'D:\anescom_edo\legacy\py'
$leg = [ordered]@{
  'legacy/finplan_articles.py' = '99e6502cdd34'
  'legacy/zay_match.py' = 'd99015f0c21f'
  'legacy/finplan_build.py' = '79a96652ace6'
}
foreach ($f in $leg.Keys) {
  $out = Join-Path $lp (Split-Path $f -Leaf)
  if (Test-Path $out) { Copy-Item $out "$out.bak_$ts" }
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $leg[$f]) { "СТОП: хэш $f = $hh"; return }
}
$py = if (Test-Path "$d\.venv\Scripts\python.exe") { "$d\.venv\Scripts\python.exe" } else { 'python' }
$z = 'D:\anescom_edo\legacy\zayavki_20261007.xls'
$zak = 'D:\anescom_edo\legacy\zayavki_avtokomp_20261019.xls'
Invoke-WebRequest "$raw/inbox/20261019/zayavki_avtokomp_b24_20261019.xls" -OutFile $zak -UseBasicParsing
if ((Get-FileHash $zak -Algorithm SHA256).Hash.Substring(0,12).ToLower() -ne 'f58f341dbd8e') { "СТОП: хэш файла заявок АВТОКОМП"; return }
if (-not (Test-Path $z)) { "СТОП: нет файла заявок $z"; return }
Push-Location $lp; $env:PYTHONIOENCODING = 'utf-8'
& $py finplan_build.py $z $zak | Select-Object -Last 14
Pop-Location
$tmp = Join-Path $env:TEMP "edo_v6d_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v6d"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
"файлы обновлены ($($files.Count)), резервная копия: $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
if (-not $ok) { "ОТКАТ: health не прошёл"; foreach ($f in $files.Keys) { $b = Join-Path $bk ($f -replace '/', '_'); $dst = Join-Path $d ($f -replace '/', '\'); if (Test-Path $b) { Copy-Item $b $dst -Force } else { Remove-Item $dst -ea 0 } }; Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'; return }
$chk = Join-Path $lp 'finplan_check.py'
Invoke-WebRequest "$raw/deploy/finplan_check.py" -OutFile $chk -UseBasicParsing
Push-Location $d; & $py $chk | Select-Object -First 60; Pop-Location
try { $r = Invoke-WebRequest "http://127.0.0.1:8096/dash/finplan/print?scope=all" -UseBasicParsing -TimeoutSec 60; "/dash/finplan/print : $($r.StatusCode)" } catch { "/dash/finplan/print : ОШИБКА $($_.Exception.Message)" }
try { $r = Invoke-WebRequest http://127.0.0.1:8096/dash/finplan -UseBasicParsing -TimeoutSec 60; "/dash/finplan : $($r.StatusCode) (без входа — форма входа)" } catch { "/dash/finplan : ОШИБКА $($_.Exception.Message)" }
"Откат: файлы из $bk."
