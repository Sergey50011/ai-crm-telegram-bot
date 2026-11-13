# Вынос проекта в сеть (кратко)

Проект рассчитан на **локальный** запуск. Для публичного доступа нужны доработки.

## Telegram-бот

- Запуск на VPS (Linux) или PaaS: `python main.py` под **systemd** / **supervisor**.
- Переменные из `.env` на сервере, не в репозитории.
- Стабильный интернет; OpenRouter доступен с сервера.

## Веб-админка

- За reverse-proxy (**nginx** + **HTTPS** Let's Encrypt).
- Обязательно задайте `DASHBOARD_PASSWORD` в `.env`.
- Не открывайте Flask напрямую в интернет без TLS и пароля.

## База

- Для одного сервера достаточно `orders.db` на диске.
- Регулярный бэкап: `python scripts/backup_orders_db.py` (папка `backups/`, на сервере — cron раз в сутки).

## Пример systemd (бот)

```ini
[Unit]
Description=CRM booking bot
After=network.target

[Service]
WorkingDirectory=/opt/crm-booking-bot
EnvironmentFile=/opt/crm-booking-bot/.env
ExecStart=/opt/crm-booking-bot/.venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Админку — отдельный unit с `python app.py` или gunicorn/waitress за nginx.
