# Деплой 18.10.2026 (v4v): подписание ч.2 — сроки по ролям, автонапоминания (задача «ANESCOM sign remind» каждый час),
# отказ от подписания с причиной, массовая подпись в кабинете («Мои подписи»), штамп «отклонено».
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$d = 'D:\anescom_edo'; $ts = Get-Date -f yyyyMMdd_HHmmss
$raw = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/0ef147f5d7726ab9595bc307b66ad5d46d73c8ac"
$files = [ordered]@{
  'app/workflow.py' = 'ec346bbf5378'
  'app/registry.py' = 'd35500f82722'
  'app/config.py' = 'd6604acb3957'
  'app/main.py' = '465e4e7bd3e3'
  'app/pdfstamp.py' = 'f90ac2d0613e'
  'app/templates/sign.html' = '53dcbe266712'
  'app/templates/cabinet.html' = 'ac9caeb94594'
  'app/templates/cabinet_doc.html' = '872fabca345d'
  'deploy/sign_remind.py' = 'c6d19a3622f3'
}
# код на сервере должен быть версии v4u (иначе — стоп)
$expect = @{ 'app\main.py' = '59694785c257'; 'app\workflow.py' = '78a65ac3af7d'; 'app\registry.py' = '5a24ee577102' }
foreach ($k in $expect.Keys) {
  $cur = (Get-FileHash "$d\$k" -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  "server $k : $cur (ожидали $($expect[$k]))"
  if ($cur -ne $expect[$k]) { "СТОП: $k на сервере отличается"; return }
}
$tmp = Join-Path $env:TEMP "edo_v4v_$ts"; New-Item -ItemType Directory $tmp | Out-Null
foreach ($f in $files.Keys) {
  $out = Join-Path $tmp ($f -replace '/', '_')
  Invoke-WebRequest "$raw/$f" -OutFile $out -UseBasicParsing
  $hh = (Get-FileHash $out -Algorithm SHA256).Hash.Substring(0,12).ToLower()
  if ($hh -ne $files[$f]) { "СТОП: хэш $f = $hh"; return }
}
$bk = "$d\backup_${ts}_v4v"; New-Item -ItemType Directory $bk | Out-Null
Copy-Item "$d\data\edo.sqlite3" (Join-Path $bk 'edo.sqlite3')
foreach ($f in $files.Keys) {
  $dst = if ($f -eq 'deploy/sign_remind.py') { "$d\sign_remind.py" } else { Join-Path $d ($f -replace '/', '\') }
  if (Test-Path $dst) { Copy-Item $dst (Join-Path $bk ($f -replace '/', '_')) }
  Copy-Item (Join-Path $tmp ($f -replace '/', '_')) $dst -Force
}
Remove-Item $tmp -Recurse
"файлы обновлены, резервная копия (вкл. базу документов): $bk"
Stop-ScheduledTask 'ANESCOM EDO'; Start-Sleep 2; Start-ScheduledTask 'ANESCOM EDO'
$ok = $false
for ($i = 0; $i -lt 12; $i++) { Start-Sleep 5; try { if ((Invoke-WebRequest http://127.0.0.1:8096/health -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { $ok = $true; break } } catch {} }
"health: $ok"
$act = New-ScheduledTaskAction -Execute "$d\.venv\Scripts\python.exe" -Argument "$d\sign_remind.py" -WorkingDirectory $d
$trg = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddHours(9).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName 'ANESCOM sign remind' -Action $act -Trigger $trg -User 'SYSTEM' -RunLevel Highest -Force | Out-Null
"задача ANESCOM sign remind: " + (Get-ScheduledTask 'ANESCOM sign remind').State
& "$d\.venv\Scripts\python.exe" "$d\sign_remind.py" --print
"Откат: файлы и edo.sqlite3 из $bk."
