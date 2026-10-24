# Подключение к КОПИИ базы (D:\Base\1C\KA2026) через COM. Пароль вводит пользователь (в окне PowerShell, не в чат).
# Запуск: . .\com_connect.ps1   (с точкой — $global:ib остаётся для следующих скриптов)
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$u = Read-Host 'Пользователь 1С (Enter = Болатұлы Бауыржан)'
if (-not $u) { $u = 'Болатұлы Бауыржан' }
$s = Read-Host 'Пароль копии' -AsSecureString
$pw = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))
$global:c1 = New-Object -ComObject V83.COMConnector
$global:ib = $global:c1.Connect("File=""D:\Base\1C\KA2026"";Usr=""$u"";Pwd=""$pw"";")
Remove-Variable pw, s
if ($global:ib) { 'ПОДКЛЮЧЕНО к копии; регистр БУ: ' + ($ib.Метаданные.РегистрыБухгалтерии | Select-Object -First 1).Имя }
