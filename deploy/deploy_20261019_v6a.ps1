# Деплой v6a: фин. план — план IT 2026 из PDF, ГПХ и подотчёт → ФОТ (6о)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/8d9d1a1bf109c8fc555fc91f71e108bdc0f3d036"
$files = [ordered]@{
  'app/finplan.py' = '477bba0646b9'
  'app/finplan_it2026.py' = 'abe2bc3e525e'
  'app/templates/dash_finplan.html' = 'c0538dfe213b'
}
# 1) скрипты фин. плана → D:\anescom_edo\legacy\py и сборка факта (an_fin_fact) до перезапуска портала
$lp = 'D:\anescom_edo\legacy\py'
$leg = [ordered]@{
  'legacy/finplan_articles.py' = '5bedb5b5b913'
  'legacy/zay_match.py' = '2e4616a32866'
  'legacy/finplan_build.py' = '6ac6cc04933a'
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
if (-not (Test-Path $z)) { "СТОП: нет файла заявок $z"; return }
Push-Location $lp; $env:PYTHONIOENCODING = 'utf-8'
& $py finplan_build.py $z | Select-Object -Last 14
Pop-Location
$tmp = Join-Path $env:TEMP "edo_v6a_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v6a"; New-Item -ItemType Directory $bk | Out-Null
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
try { $r = Invoke-WebRequest http://127.0.0.1:8096/dash/finplan -UseBasicParsing -TimeoutSec 60; "/dash/finplan : $($r.StatusCode) (без входа — форма входа)" } catch { "/dash/finplan : ОШИБКА $($_.Exception.Message)" }
"Откат: файлы из $bk."
