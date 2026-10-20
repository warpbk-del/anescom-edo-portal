# Деплой 20.10.2026: новый адрес портала https://my.anescom.kz, edo.anescom.kz — редирект 301
# (кроме /api/*, /b24/*, /health — их по-прежнему обслуживает портал: 1С, вебхуки и приложение Bitrix24).
# Плюс удаление временного app\static\vo_tmp.zip. Запуск: админ-PowerShell на сервере.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/89128b7ca6642f8f64ed9c00228e114ac566c035"
$files = [ordered]@{
  'app/workflow.py' = 'ea15baa5d010'
  'app/config.py' = '984a3b43f172'
  'app/dashboards.py' = '8e51c7192162'
  'app/helppages.py' = 'bab1156a0422'
  'app/main.py' = 'b1a88798e14c'
  'app/xlsx_out.py' = '9e4e5c520d92'
  'app/templates/cabinet.html' = '3e0bc4b3325c'
  'app/templates/cabinet_doc.html' = '5f829e2aae42'
  'app/templates/cabinet_new.html' = 'a726a79a6b05'
  'app/templates/my_admin.html' = '790d7cc916e7'
  'app/templates/noaccess.html' = 'c62b2dce4fc7'
  'app/templates/report.html' = '69e5eba7119c'
  'app/templates/roles.html' = '8d7d81dfe7c7'
}
$utf8 = New-Object System.Text.UTF8Encoding($false)
# 0. DNS
$ip = try { ([Net.Dns]::GetHostAddresses('my.anescom.kz') | Select-Object -First 1).IPAddressToString } catch { '' }
"DNS my.anescom.kz -> $ip"
if ($ip -ne '213.232.246.42') { 'СТОП: DNS my.anescom.kz ещё не указывает на 213.232.246.42'; return }
# 1. файлы портала
$tmp = Join-Path $env:TEMP "edo_my_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_my"; New-Item -ItemType Directory $bk | Out-Null
foreach ($f in $files.Keys) { $src = Join-Path $d ($f -replace '/', '\'); if (Test-Path $src) { Copy-Item $src (Join-Path $bk ($f -replace '/', '_')) } }
Copy-Item "$d\config.env" "$bk\config.env"
# 2. Caddy: сайт my.anescom.kz (копия блока edo.anescom.kz)
$cf = 'D:\caddy\Caddyfile'; $ce = Get-ChildItem D:\caddy -Filter caddy*.exe | Select-Object -First 1 -Expand FullName
Copy-Item $cf "$cf.bak_${ts}_my"; Copy-Item $cf "$bk\Caddyfile"
$txt = [IO.File]::ReadAllText($cf)
$m = [regex]::Match($txt, '(?m)^[ \t]*edo\.anescom\.kz[^\r\n{]*\{')
if (-not $m.Success) { 'СТОП: в Caddyfile нет блока edo.anescom.kz'; return }
$i = $m.Index + $m.Length; $depth = 1
while ($depth -gt 0 -and $i -lt $txt.Length) { $c = $txt[$i]; if ($c -eq '{') { $depth++ } elseif ($c -eq '}') { $depth-- }; $i++ }
$edoBlock = $txt.Substring($m.Index, $i - $m.Index)
$inner = $txt.Substring($m.Index + $m.Length, $i - 1 - $m.Index - $m.Length)
if ($txt -match '(?m)^[ \t]*my\.anescom\.kz') { 'Caddyfile: блок my.anescom.kz уже есть' }
else {
  $myBlock = "my.anescom.kz {" + ($inner -replace 'access_edo', 'access_my') + "}"
  $txt = $txt.Replace($edoBlock, $myBlock + "`r`n`r`n" + $edoBlock)
  [IO.File]::WriteAllText($cf, $txt, $utf8)
}
& $ce validate --config $cf --adapter caddyfile 2>&1 | Select-Object -Last 2
if ($LASTEXITCODE -ne 0) { 'ОТКАТ Caddyfile: validate не прошёл'; Copy-Item "$bk\Caddyfile" $cf -Force; return }
& $ce reload --config $cf --adapter caddyfile 2>&1 | Select-Object -Last 2
$ok = $false
for ($k = 0; $k -lt 24; $k++) { Start-Sleep 5; try { if ((Invoke-WebRequest https://my.anescom.kz/health -UseBasicParsing -TimeoutSec 8).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"https://my.anescom.kz/health: $ok"
if (-not $ok) { 'СТОП: сертификат/доступ my.anescom.kz не готов; edo.anescom.kz не трогали, файлы портала не меняли'; return }
# 3. файлы портала + EDO_PUBLIC_BASE_URL
foreach ($f in $files.Keys) { Copy-Item (Join-Path $tmp ($f -replace '/', '_')) (Join-Path $d ($f -replace '/', '\')) -Force }
Remove-Item $tmp -Recurse
$env_ = [IO.File]::ReadAllText("$d\config.env").TrimStart([char]0xFEFF)
$env_ = [regex]::Replace($env_, '(?m)^EDO_PUBLIC_BASE_URL=.*$', 'EDO_PUBLIC_BASE_URL=https://my.anescom.kz')
[IO.File]::WriteAllText("$d\config.env", $env_, $utf8)
(Get-Content "$d\config.env" | ? { $_ -match '^EDO_PUBLIC_BASE_URL=' })
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($k = 0; $k -lt 12; $k++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health портала: $ok"
if (-not $ok) { 'ОТКАТ портала'; foreach ($f in $files.Keys) { $b = Join-Path $bk ($f -replace '/', '_'); if (Test-Path $b) { Copy-Item $b (Join-Path $d ($f -replace '/', '\')) -Force } }; Copy-Item "$bk\config.env" "$d\config.env" -Force; Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'; return }
# 4. edo.anescom.kz -> редирект (API, Bitrix24 и health остаются на портале)
$txt = [IO.File]::ReadAllText($cf)
$redir = "edo.anescom.kz {`r`n`t@keep path /api/* /b24/* /health`r`n`thandle @keep {`r`n`t`treverse_proxy 127.0.0.1:8096`r`n`t}`r`n`thandle {`r`n`t`tredir https://my.anescom.kz{uri} 301`r`n`t}`r`n}"
$txt = $txt.Replace($edoBlock, $redir); [IO.File]::WriteAllText($cf, $txt, $utf8)
& $ce validate --config $cf --adapter caddyfile 2>&1 | Select-Object -Last 1
if ($LASTEXITCODE -ne 0) { 'Caddyfile с редиректом не прошёл validate — оставлен прежний edo'; $txt = $txt.Replace($redir, $edoBlock); [IO.File]::WriteAllText($cf, $txt, $utf8) }
else { & $ce reload --config $cf --adapter caddyfile 2>&1 | Select-Object -Last 1 }
Start-Sleep 3
foreach ($u in 'https://edo.anescom.kz/cabinet', 'https://edo.anescom.kz/health', 'https://my.anescom.kz/cabinet', 'https://bot.anescom.kz/dogovor/health') {
  try { $r = Invoke-WebRequest $u -UseBasicParsing -MaximumRedirection 0 -TimeoutSec 15 -ea 0; "$u : $($r.StatusCode) $($r.Headers.Location)" } catch { "$u : $($_.Exception.Message)" }
}
# 5. временный файл озвучки
$vo = "$d\app\static\vo_tmp.zip"
if (Test-Path $vo) { Remove-Item $vo -Force; "удалён $vo" } else { "нет файла $vo" }
"Готово. Откат: файлы, config.env и Caddyfile в $bk"
