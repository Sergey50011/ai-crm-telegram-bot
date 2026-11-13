# Подключение Google Sheets

После подтверждения заявки в Telegram в таблицу добавляется **новая строка** (SQLite остаётся главным хранилищем).

## 1. Google Cloud

1. [Google Cloud Console](https://console.cloud.google.com/) → проект → **APIs & Services** → включить **Google Sheets API**.
2. **Credentials** → **Create service account** → скачать JSON-ключ.
3. Положить файл в проект, например `secrets/google-sa.json` (папка в `.gitignore`).

## 2. Таблица

1. Создать Google Таблицу.
2. **Настройки доступа** → выдать права **Редактор** на email сервис-аккаунта из JSON (поле `client_email`).
3. Скопировать **ID таблицы** из URL:  
   `https://docs.google.com/spreadsheets/d/<GOOGLE_SHEETS_ID>/edit`

## 3. `.env`

```env
SHEETS_ENABLED=1
GOOGLE_SHEETS_ID=ваш_id_таблицы
GOOGLE_SHEETS_WORKSHEET=Заявки
GOOGLE_SERVICE_ACCOUNT_FILE=secrets/google-sa.json
```

## 4. Зависимости

```bash
pip install -r requirements.txt
```

## 5. Проверка

Подтвердите тестовую заявку в боте — в листе «Заявки» появится строка с заголовками.

Если Sheets недоступен, заявка **всё равно сохраняется** в SQLite; ошибка пишется в лог.
