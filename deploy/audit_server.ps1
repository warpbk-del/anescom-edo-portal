# Аудит сервера (только чтение, ничего не меняет). 20.10.2026
$ErrorActionPreference = 'SilentlyContinue'
function L($k, $v) { "{0,-22} {1}" -f $k, $v }
$os = Get-CimInstance Win32_OperatingSystem; $cs = Get-CimInstance Win32_ComputerSystem
$lic = Get-CimInstance SoftwareLicensingProduct -Filter "PartialProductKey IS NOT NULL AND Name LIKE 'Windows%'" | Select-Object -First 1
L 'ОС' "$($os.Caption) $($os.Version) | активация: $(@{0='нет';1='да';5='уведомление'}[[int]$lic.LicenseStatus]) ($($lic.LicenseStatus))"
L 'Аптайм/загрузка' ("{0:dd.MM HH:mm}, {1:N0} дн" -f $os.LastBootUpTime, ((Get-Date) - $os.LastBootUpTime).TotalDays)
$cpu = (Get-CimInstance Win32_Processor | Measure-Object LoadPercentage -Average).Average
L 'CPU/RAM' ("{0} ядер, загрузка {1}% | RAM {2:N1}/{3:N1} ГБ свободно" -f $cs.NumberOfLogicalProcessors, $cpu, ($os.FreePhysicalMemory/1MB), ($os.TotalVisibleMemorySize/1MB))
L 'Диски' ((Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | % { "{0} {1:N0}/{2:N0} ГБ своб." -f $_.DeviceID, ($_.FreeSpace/1GB), ($_.Size/1GB) }) -join ' | ')
$hf = Get-HotFix | ? InstalledOn | Sort-Object InstalledOn -Descending | Select-Object -First 1
L 'Посл. обновление' "$($hf.HotFixID) $('{0:dd.MM.yyyy}' -f $hf.InstalledOn)"
try { $s = (New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher().Search("IsInstalled=0 and Type='Software'")
  L 'Ждут установки' ("{0} шт. (из них безопасность: {1})" -f $s.Updates.Count, @($s.Updates | ? { $_.MsrcSeverity }).Count) } catch { L 'Ждут установки' 'не удалось проверить' }
$mp = Get-MpComputerStatus
if ($mp) { L 'Defender' ("служба {0}, защита в реальном времени {1}, базы {2} дн., посл. скан {3:dd.MM}" -f $mp.AMServiceEnabled, $mp.RealTimeProtectionEnabled, $mp.AntivirusSignatureAge, $mp.QuickScanEndTime) } else { L 'Defender' 'нет/не отвечает' }
L 'Другие антивирусы' ((Get-Service | ? { $_.DisplayName -match 'Sophos|Kaspersky|ESET|Dr\.?Web|Avast|Symantec|McAfee|Bitdefender' -and $_.Status -eq 'Running' } | % DisplayName) -join ', ')
L 'Брандмауэр' ((Get-NetFirewallProfile | % { "$($_.Name)=$($_.Enabled)" }) -join ' ')
$rdp = Get-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server'
$nla = (Get-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp').UserAuthentication
$rp = (Get-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp').PortNumber
L 'RDP' ("включён {0}, порт {1}, NLA {2}" -f ($rdp.fDenyTSConnections -eq 0), $rp, ($nla -eq 1))
L 'SMBv1' ((Get-SmbServerConfiguration).EnableSMB1Protocol)
$na = net accounts
L 'Блокировка учёток' (($na | ? { $_ -match 'lockout threshold|Пороговое|блокировк' }) -join '; ' -replace '\s{2,}', ' ')
L 'Мин. длина пароля' (($na | ? { $_ -match 'Minimum password length|Минимальная длина' }) -replace '.*\s', '')
$adm = Get-LocalGroupMember -SID 'S-1-5-32-544' | % Name
L 'Администраторы' ("{0}: {1}" -f @($adm).Count, ($adm -join ', '))
$ba = Get-LocalUser | ? { $_.SID -like '*-500' }
L 'Встр. Administrator' ("{0}, включён {1}" -f $ba.Name, $ba.Enabled)
$f = Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4625; StartTime=(Get-Date).AddDays(-1)} -MaxEvents 20000
$top = $f | % { $_.Properties[19].Value } | ? { $_ -and $_ -ne '-' } | Group-Object | Sort-Object Count -Descending | Select-Object -First 3 | % { "$($_.Name)×$($_.Count)" }
L 'Неудачные входы 24ч' ("{0} шт.; IP: {1}" -f @($f).Count, ($top -join ', '))
$ok = Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4624; StartTime=(Get-Date).AddDays(-1)} -MaxEvents 5000 | ? { $_.Properties[8].Value -eq 10 }
L 'RDP-входы 24ч' ((($ok | % { "$($_.Properties[5].Value)@$($_.Properties[18].Value)" } | Group-Object | % { "$($_.Name)×$($_.Count)" }) -join ', '))
$wb = wbadmin get versions 2>$null | Select-String 'Время архивации|Backup time|Конечный объект|Backup target' | Select-Object -Last 2
L 'Резервные копии' (($wb | % { $_.Line.Trim() }) -join ' | ')
$pol = Get-WBPolicy; if ($pol) { L 'Цель архивации' ((Get-WBBackupTarget $pol | % { "$($_.TargetType) $($_.Label) $($_.TargetPath)" }) -join '; ') }
$lst = Get-NetTCPConnection -State Listen | ? { $_.LocalAddress -in '0.0.0.0', '::' } | Sort-Object LocalPort -Unique
L 'Слушают все адреса' (($lst | % { "$($_.LocalPort):$((Get-Process -Id $_.OwningProcess).ProcessName)" }) -join ' ')
L 'Задачи ANESCOM' ((Get-ScheduledTask | ? TaskName -like 'ANESCOM*' | % { "$($_.TaskName -replace 'ANESCOM ','')=$($_.State)" }) -join ', ')
L 'Caddy/TLS' ((Get-Process caddy*).Count -gt 0)
