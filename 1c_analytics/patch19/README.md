Патч проекта 19 к ану_Аналитика (версия 0d7dcf7 → текущая). Вставлялся в копию по частям через буфер обмена сервера:
1_region.bsl — перед «#Область ПроизводствоАВТОКОМП»; 2_kinds.bsl — после «Возврат СебестоимостьПоМесяцам(Начало, Конец, Ошибки);» (в ДанныеВида);
3: «purchases,cost_month» → «purchases,cost_month,order_clients»; 4: «prod_orders,prod_raw» → «prod_orders,prod_raw,partners»;
5_diag.bsl — после «ПопробоватьВид("cost_month", …);» в Диагностика.
