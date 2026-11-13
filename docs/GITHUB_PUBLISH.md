# Публикация на GitHub

Проект подготовлен: секреты и БД в `.gitignore`, скрины в `portfolio-screenshots/00-hh-poryadok/`.

## 1. Установить Git (если ещё нет)

https://git-scm.com/download/win — после установки перезапустите терминал.

## 2. Создать пустой репозиторий на GitHub

https://github.com/new — имя, например `ai-crm-telegram-bot`, **без** README и .gitignore.

## 3. Первый push (PowerShell)

```powershell
cd $HOME\Desktop\crm-booking-bot
git init
git add .
git status
```

Убедитесь, что **нет** `.env`, `orders.db`, файлов в `secrets/*.json`.

```powershell
git commit -m "Initial commit: Telegram CRM booking bot"
git branch -M main
git remote add origin https://github.com/ВАШ_ЛОГИН/ai-crm-telegram-bot.git
git push -u origin main
```

## 4. После push

Обновите ссылку в `docs/HH_PORTFOLIO.md` и в резюме на hh.ru.
