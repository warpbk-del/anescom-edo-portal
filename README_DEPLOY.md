# Деплой портала ЭДО АНЕСКОМ на сервер

Хост: тот же сервер, что и бот (bot.anescom.kz, за caddy). Каталог: `D:\anescom_edo`.

## 1. Файлы
Распаковать архив портала в `D:\anescom_edo` (структура: `app\`, `requirements.txt`,
`config.env`, `start_edo.bat`).

## 2. Виртуальное окружение и зависимости
```
cd /d D:\anescom_edo
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
```

## 3. Конфигурация
Проверить `D:\anescom_edo\config.env`:
- EDO_PUBLIC_BASE_URL=https://bot.anescom.kz/dogovor
- EDO_ROOT_PATH=/dogovor
- EDO_API_TOKEN=... (этот же токен прописать в 1С)
- EDO_STAFF_PASSWORD=... (пароль входа в кабинет)
- EDO_B24_WEBHOOK=... (вебхук Bitrix24 для WhatsApp — задача #54)

## 4. Проверка запуска
```
D:\anescom_edo\start_edo.bat
```
В другом окне: `curl http://127.0.0.1:8096/health` → {"ok":true,...}

## 5. caddy
Добавить в блок сайта bot.anescom.kz содержимое `caddy_dogovor.txt`, перезагрузить caddy.
Проверить снаружи: https://bot.anescom.kz/dogovor/health

## 6. Автозапуск (Планировщик, как у бота)
```
schtasks /Create /TN "ANESCOM EDO" /TR "D:\anescom_edo\start_edo.bat" /SC ONSTART /RU SYSTEM /RL HIGHEST /F
schtasks /Run /TN "ANESCOM EDO"
```

## Проверка
- Кабинет: https://bot.anescom.kz/dogovor/cabinet  (пароль из EDO_STAFF_PASSWORD)
- Создание документа (из 1С или curl): POST https://bot.anescom.kz/dogovor/api/documents
  с заголовком `Authorization: Bearer <EDO_API_TOKEN>`.
