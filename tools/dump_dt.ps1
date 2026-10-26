# Выгрузка файловой базы 1С в .dt (21-П-В). Пароль вводит пользователь. Запуск:
# iex (iwr -UseBasicParsing https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/<sha>/tools/dump_dt.ps1).Content
$name = if ($env:DT_BASE) { $env:DT_BASE } else { 'ANESCOM_FIX' }
$ib  = "D:\Base\1C\$name"
$dir = 'D:\Base\1C\Выгрузки'; New-Item -ItemType Directory -Force -Path $dir | Out-Null
$out = Join-Path $dir ("$($name)_" + (Get-Date -Format 'dd-MM-yyyy_HH-mm') + '.dt')
$log = Join-Path $dir "dump_$name.log"
$exe = (Get-ChildItem 'C:\Program Files\1cv8\8.3.*\bin\1cv8.exe' | Sort-Object FullName | Select-Object -Last 1).FullName
$sz = (Get-Item "$ib\1Cv8.1CD").Length / 1GB; $free = (Get-PSDrive D).Free / 1GB
Write-Host ('База {0:N1} ГБ, свободно на D: {1:N1} ГБ' -f $sz, $free)
$procs = Get-CimInstance Win32_Process -Filter "Name like '1cv8%'" | Where-Object { $_.CommandLine -match $name }
if ($procs) { Write-Host "ВНИМАНИЕ: открыты процессы 1С с базой $($name):"; $procs | ForEach-Object { Write-Host '  PID' $_.ProcessId $_.CommandLine.Substring(0, [Math]::Min(120, $_.CommandLine.Length)) } }
$u = Read-Host "Пользователь 1С ($name)"
$sp = Read-Host 'Пароль (звёздочки)' -AsSecureString
$p = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sp))
Write-Host 'Выгрузка начата' (Get-Date -Format 'HH:mm:ss') '→' $out
$args1 = @('DESIGNER', '/F', "`"$ib`"", '/N', "`"$u`"", '/P', "`"$p`"", '/DisableStartupDialogs', '/DisableStartupMessages', '/DumpIB', "`"$out`"", '/Out', "`"$log`"")
$pr = Start-Process -FilePath $exe -ArgumentList $args1 -Wait -PassThru; $p = $null
Write-Host 'Готово' (Get-Date -Format 'HH:mm:ss') 'код' $pr.ExitCode
Get-Content $log -ErrorAction SilentlyContinue | Select-Object -Last 5
if (Test-Path $out) { Write-Host ('DT {0} {1:N2} ГБ' -f $out, ((Get-Item $out).Length / 1GB)) } else { Write-Host 'DT НЕ СОЗДАН' }
