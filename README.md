# Telegram-бот автосервиса + веб-админка

Асинхронный бот принимает заявки в свободной форме, извлекает поля через OpenRouter (LLM), валидирует имя и телефон и сохраняет лиды в SQLite (`orders.db`). Локальная панель на Flask — список заявок, статистика и смена статусов.

## Требования

- Python 3.10+
- Аккаунт OpenRouter и API-ключ
- Токен бота от [@BotFather](https://t.me/BotFather)

## Быстрый старт (Windows, PowerShell)

```powershell
cd путь\к\crm-booking-bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

В `.env` укажите `BOT_TOKEN`, `OPENROUTER_API_KEY`. Для ограничения команды `/admin` — `ADMIN_ID` (узнать id: [@userinfobot](https://t.me/userinfobot)).

**Бот:**

```powershell
python main.py
```

**Веб-админка** (отдельный терминал):

```powershell
python app.py
```

Откройте http://127.0.0.1:5000

## Структура проекта

| Файл / папка | Назначение |
|--------------|------------|
| `main.py` | Запуск Telegram-бота (polling) |
| `handlers.py` | `/start`, текст заявок, `/admin` |
| `ai_service.py` | OpenRouter + Pydantic |
| `lead_validation.py` | Отсев мусора, имя и телефон перед записью в БД |
| `db_schema.py` | Общая схема SQLite (бот + Flask) |
| `leads_service.py` | Сценарии: заявка из текста, смена статуса |
| `database.py` | SQLite (aiosqlite), таблица `leads` |
| `app.py` | Flask: REST API и дашборд |
| `templates/index.html` | UI админки |
| `portfolio-screenshots/00-hh-poryadok/` | Скрины для hh (01–08) |
| `docs/HH_PORTFOLIO.md` | Текст для резюме / hh |
| `docs/GITHUB_PUBLISH.md` | Как залить репозиторий на GitHub |
| `portfolio/` | Демо-данные и пересъёмка скринов |

## Таблица `leads`

Колонки: `id`, `telegram_id`, `name`, `phone`, `service`, `date`, `created_at`, `updated_at`, `status` (`new` | `in_progress` | `completed`).

Тесты: `python -m pytest tests/`

## Поведение бота

- Короткий или пустой ввод (`?`, без телефона) **не сохраняется** — бот просит указать имя, телефон и суть обращения.
- Сбой OpenRouter (таймаут, 5xx, пустой JSON) — отдельное сообщение «сервис распознавания недоступен»; при включённом `BOT_FALLBACK_PARSE` бот попробует вытащить имя и телефон regex, остальной текст — в услугу.
- После успешной заявки поля нормализуются (имя с заглавной, телефон в едином формате, если распознан РФ-номер).
- Клиент получает номер заявки (`Заявка #id`). В `/admin` у каждой строки указан статус.
- **Подтверждение:** после разбора ИИ — кнопки «Подтвердить / Отменить».
- **Дедупликация:** повтор того же телефона за 24 ч не создаёт новую заявку.
- **Уведомление:** при `ADMIN_ID` и `NOTIFY_ON_NEW_LEAD=1` админу приходит сообщение о новой заявке.
- **Статус из Telegram:** `/setstatus 5 in_progress` (только admin).
- **Дашборд:** поиск и фильтр по статусу.

Вынос в интернет: см. [DEPLOY.md](DEPLOY.md).  
Инструкция для заказчика (печать / PDF): [docs/ИНСТРУКЦИЯ_КЛИЕНТУ.md](docs/ИНСТРУКЦИЯ_КЛИЕНТУ.md).  
Google Sheets: [docs/GOOGLE_SHEETS.md](docs/GOOGLE_SHEETS.md) (`SHEETS_ENABLED=1`).

Демо-данные для скринов: `python portfolio/seed_demo_data.py --replace` (без флага живые заявки не удаляются).

## Безопасность

- **Не коммитьте `.env`** в git. Если ключи светились — revoke в @BotFather и на openrouter.ai, выпустите новые.
- **`DASHBOARD_PASSWORD`** в `.env` — **обязателен** (≥8 символов); Basic Auth для http://127.0.0.1:5000 (логин `DASHBOARD_USERNAME`, по умолчанию `admin`).
- **`ADMIN_ID`** или **`ADMIN_IDS`** (через запятую) — кто вызывает `/admin` и `/setstatus`; пусто — демо-режим (всем).
- **`BOT_RATE_LIMIT_PER_MIN`** — лимит отдельных сообщений в минуту (по умолчанию 5).
- **`BOT_MAX_MESSAGE_CHARS`** — макс. длина одного сообщения (по умолчанию 600).
- **`BOT_REPEAT_LINE_THRESHOLD`** — отклонять копипаст: столько одинаковых длинных строк подряд (по умолчанию 3).
- `LOG_LEVEL=DEBUG` — в консоли сырой текст и JSON от OpenRouter (для отладки, не на проде).
