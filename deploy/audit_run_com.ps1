# Запуск выгрузки аудита (проект 21) в КОПИИ базы ANESCOM-KA 2026 через COM-соединение (только чтение данных 1С).
# Результат: портал /audit; журнал — D:\anescom_edo\data\reports\audit_run.txt
$log = 'D:\anescom_edo\data\reports\audit_run.txt'
"старт $(Get-Date -f 'yyyy-MM-dd HH:mm:ss')" | Out-File $log -Encoding UTF8
try {
  $c = New-Object -ComObject V83.COMConnector
  $usr = 'Болатұлы Бауыржан'
  $ib = $c.Connect("File=""D:\Base\1C\KA2026"";Usr=""$usr"";")
  "соединение есть" | Out-File $log -Append -Encoding UTF8
  $m = $ib.ану_Аналитика
  [void]$m.ВыгрузитьАудит()
  "готово $(Get-Date -f 'HH:mm:ss')" | Out-File $log -Append -Encoding UTF8
} catch {
  "ОШИБКА: $($_.Exception.Message)" | Out-File $log -Append -Encoding UTF8
}
