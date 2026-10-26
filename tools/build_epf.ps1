# Сборка внешней обработки 1С из XML-исходников репозитория (21-32 ANU_NachStr).
# Запуск на сервере: iex (iwr -UseBasicParsing https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/<sha>/tools/build_epf.ps1).Content
param([string]$Sha = $env:EPF_SHA)
$ErrorActionPreference = 'Stop'
if (-not $Sha) { $Sha = 'main' }
$base = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/$Sha/1c_homepage/src"
$dst  = 'D:\anescom_edo\1c_homepage\src'
$files = @('ANU_NachStr.xml','ANU_NachStr/Forms/Форма.xml','ANU_NachStr/Forms/Форма/Ext/Form.xml','ANU_NachStr/Forms/Форма/Ext/Form/Module.bsl')
foreach ($f in $files) {
  $p = Join-Path $dst ($f -replace '/','\')
  New-Item -ItemType Directory -Force -Path (Split-Path $p) | Out-Null
  $enc = (($f -split '/') | ForEach-Object { [uri]::EscapeDataString($_) }) -join '/'
  $u = "$base/$enc"
  Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $p
  Write-Host 'OK' $f (Get-Item $p).Length
}
$exe = Get-ChildItem 'C:\Program Files\1cv8\8.3.*\bin\1cv8.exe' | Sort-Object FullName | Select-Object -Last 1
Write-Host 'PLATFORM' $exe.FullName
$ib = 'D:\Base\1C\EMPTY_EPF'
if (-not (Test-Path "$ib\1Cv8.1CD")) {
  & $exe.FullName CREATEINFOBASE "File=`"$ib`"" /Out "D:\anescom_edo\1c_homepage\create.log" | Out-Null
  Start-Sleep 2; Get-Content "D:\anescom_edo\1c_homepage\create.log" -ErrorAction SilentlyContinue
}
$out = 'D:\anescom_edo\ANU_NachStr.epf'
$log = 'D:\anescom_edo\1c_homepage\build.log'
$p = Start-Process -FilePath $exe.FullName -ArgumentList @('DESIGNER','/F',"`"$ib`"",'/DisableStartupDialogs','/LoadExternalDataProcessorOrReportFromFiles',"`"$dst\ANU_NachStr.xml`"","`"$out`"",'/Out',"`"$log`"") -Wait -PassThru
Write-Host 'EXIT' $p.ExitCode
Get-Content $log -ErrorAction SilentlyContinue
if (Test-Path $out) { Write-Host 'EPF' $out (Get-Item $out).Length (Get-Item $out).LastWriteTime } else { Write-Host 'EPF NOT BUILT' }
