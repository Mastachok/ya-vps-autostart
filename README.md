# 🛡️ VPS Watchdog v3.0

**Автоматический мониторинг и запуск виртуальных машин в Yandex Cloud с Telegram уведомлениями**

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](https://github.com/Mastachok/ya-vps-autostart/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://hub.docker.com/)
[![Python](https://img.shields.io/badge/python-3.11+-yellow.svg)](https://www.python.org/)

---

## 🌟 Возможности v3.0

### ✨ Множество виртуальных машин
- 📝 Неограниченное количество профилей VM
- 🔄 Одновременный мониторинг всех VM
- ⚡ Каждая VM в отдельном потоке
- 🎯 Индивидуальные настройки для каждой VM

### 📱 Telegram интеграция
- 🔴 Уведомления о падении VM
- 🟢 Уведомления о восстановлении
- ⚠️ Уведомления об ошибках
- 📊 Статус по команде
- 📜 Просмотр логов
- 🎛️ Управление через бота

### 🎨 Удобный интерфейс
- 🖥️ Интерактивное меню
- 🔐 OAuth авторизация (без yc CLI!)
- 📤 Загрузка ключей прямо в меню
- 🚀 Пошаговая настройка
- 📊 Статистика в реальном времени

### 🔧 Умный мониторинг
- ✅ Проверка статуса операций
- 🔄 Cooldown между попытками
- 📈 Статистика uptime/downtime
- 🛡️ Graceful shutdown
- 📊 Healthcheck

---

## 🚀 Быстрый старт

### Установка (одна команда!)

```bash
curl -fsSL https://raw.githubusercontent.com/Mastachok/ya-vps-autostart/main/install.sh | sudo bash
```

### Настройка

```bash
# Запусти меню
sudo vps-watchdog
```

#### 1️⃣ Добавь профиль VM (пункт 2)
- Откроется ссылка для OAuth токена
- Скрипт автоматически найдёт все твои VM
- Выбери VM для мониторинга
- Профиль создан! ✅

#### 2️⃣ Настрой Telegram (пункт 6)
- Создай бота через [@BotFather](https://t.me/botfather)
- Укажи Bot Token и Chat ID
- Получи тестовое уведомление! 📱

#### 3️⃣ Запусти мониторинг

```bash
sudo systemctl start vps-watchdog
sudo docker logs -f vps-watchdog
```

**Готово!** 🎉

---

## 📖 Подробная документация

### Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│              ЛЮБОЙ ХОСТИНГ                  YANDEX CLOUD        │
│         (Hetzner, AWS, DigitalOcean,                            │
│          даже домашний сервер)                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🟢 WATCHDOG СЕРВЕР                🔴 VM #1  🔴 VM #2  🔴 VM #3 │
│                                    (могут падать)               │
│  ┌──────────────────────┐                                       │
│  │                      │          ┌──────┐ ┌──────┐ ┌──────┐  │
│  │  VPS Watchdog v3.0   │──ping───▶│ VM 1 │ │ VM 2 │ │ VM 3 │  │
│  │                      │          └──────┘ └──────┘ └──────┘  │
│  │  • Мониторинг всех   │                                       │
│  │  • Telegram бот      │──API────▶ Запуск VM при падении      │
│  │  • Статистика        │                                       │
│  └──────────────────────┘                                       │
│           │                                                     │
│           └──────────────▶ 📱 Telegram уведомления             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Структура профилей

Каждая VM = отдельный JSON файл в `/opt/vps-watchdog/profiles/`:

```json
{
  "id": "abc12345",
  "name": "Production Server",
  "vm_host": "158.160.75.118",
  "instance_id": "epduvd41hfntv8cangem",
  "folder_id": "b1gu9rbr7jchsk26nl30",
  "enabled": true,
  "check_interval": 60,
  "ping_count": 3,
  "ping_timeout": 5,
  "cooldown_minutes": 5,
  "max_start_attempts": 3
}
```

### Настройки профиля

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `name` | Имя профиля | - |
| `vm_host` | IP адрес VM | - |
| `instance_id` | ID VM в Yandex Cloud | - |
| `enabled` | Включен ли мониторинг | `true` |
| `check_interval` | Интервал проверки (сек) | `60` |
| `ping_count` | Количество ping запросов | `3` |
| `ping_timeout` | Таймаут ping (сек) | `5` |
| `cooldown_minutes` | Пауза между попытками (мин) | `5` |
| `max_start_attempts` | Макс. попыток подряд | `3` |

---

## 📱 Telegram бот

### Создание бота

1. Напиши [@BotFather](https://t.me/botfather) в Telegram
2. Отправь команду `/newbot`
3. Придумай имя бота (например: `My VPS Watchdog`)
4. Придумай username (например: `my_vps_watchdog_bot`)
5. Скопируй токен (выглядит так: `123456:ABC-DEF...`)

### Получение Chat ID

**Способ 1: Через бота**
1. Напиши своему боту любое сообщение
2. Открой в браузере:
   ```
   https://api.telegram.org/botТВОЙ_ТОКЕН/getUpdates
   ```
3. Найди `"chat":{"id":123456789`

**Способ 2: Через @userinfobot**
1. Напиши [@userinfobot](https://t.me/userinfobot)
2. Он покажет твой Chat ID

### Команды бота (в разработке)

```
/start   - Приветствие
/status  - Статус всех VM
/logs    - Последние логи
/stats   - Статистика
/help    - Помощь
```

### Пример уведомления

```
🔴 VM Недоступна!

📊 Профиль: Production Server
🌐 IP: 158.160.75.118
⏰ Время: 17.01.2026 12:30:15
🔄 Попытка запуска: #1

⚙️ Запускаю VM через Yandex Cloud API...
```

---

## 🎨 Меню управления

```
🛡️  VPS WATCHDOG v3.0

📊 СТАТУС:
   📝 Профилей: 3 (активных: 2)
   ⚙️  Сервис: работает
   📱 Telegram: подключен

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 УПРАВЛЕНИЕ ПРОФИЛЯМИ:
  1) 📝 Список профилей
  2) ➕ Добавить профиль (OAuth)
  3) ✏️  Редактировать профиль
  4) 🗑️  Удалить профиль
  5) 🔄 Включить/выключить мониторинг

📱 TELEGRAM:
  6) 🤖 Настроить бота
  7) 📤 Тест уведомления
  8) 📊 Статус бота

⚙️  СИСТЕМА:
  9) 🔧 Управление сервисом
  10) 📜 Показать логи
  11) 📈 Статистика

ℹ️  ИНФОРМАЦИЯ:
  0) ❓ Помощь
  q) 🚪 Выход
```

---

## 🔧 Управление

### Команды systemctl

```bash
# Запустить
sudo systemctl start vps-watchdog

# Остановить
sudo systemctl stop vps-watchdog

# Перезапустить
sudo systemctl restart vps-watchdog

# Статус
sudo systemctl status vps-watchdog

# Автозапуск
sudo systemctl enable vps-watchdog
```

### Просмотр логов

```bash
# Логи контейнера
sudo docker logs -f vps-watchdog

# Последние 50 строк
sudo docker logs --tail 50 vps-watchdog

# Файл логов
tail -f /opt/vps-watchdog/logs/watchdog.log
```

### Обновление

```bash
# Сохрани профили и конфиги
sudo cp -r /opt/vps-watchdog/profiles ~/backup-profiles
sudo cp -r /opt/vps-watchdog/config ~/backup-config

# Переустанови
curl -fsSL https://raw.githubusercontent.com/Mastachok/ya-vps-autostart/main/install.sh | sudo bash

# Профили и конфиги сохранятся автоматически!
```

---

## 🆚 Отличия от v2.0

| Функция | v2.0 | v3.0 |
|---------|------|------|
| Количество VM | 1 | ♾️ Неограниченно |
| Telegram | ❌ | ✅ Полная интеграция |
| OAuth в меню | ❌ | ✅ Встроен |
| Проверка операций | ⚠️ Частично | ✅ Полная |
| Профили | ❌ | ✅ JSON профили |
| Статистика | ❌ | ✅ Uptime/downtime |
| Многопоточность | ❌ | ✅ Каждая VM в потоке |
| Миграция | - | ✅ Автоматическая |

---

## 📊 Примеры использования

### Случай 1: Один сервер, несколько VM

```
Watchdog на Hetzner VPS (€3/мес)
    ↓
Мониторит 5 VM в Yandex Cloud
```

### Случай 2: Домашний сервер

```
Raspberry Pi дома
    ↓
Мониторит продакшн VM в облаке
    ↓
Уведомления в Telegram на телефон
```

### Случай 3: Dev + Staging + Prod

```
1 Watchdog следит за:
  • Dev VM (может падать часто)
  • Staging VM (редко)
  • Production VM (критично!)
```

---

## ❓ FAQ

### Watchdog должен быть в Yandex Cloud?

**НЕТ!** Watchdog может быть где угодно:
- ✅ Hetzner, AWS, DigitalOcean
- ✅ Домашний сервер
- ✅ Другая VM в Yandex Cloud
- ✅ VPS в любом датацентре

Главное - стабильный интернет и Docker.

### Что если watchdog упадёт?

Выбирай стабильный хостинг для watchdog. Если он упадёт - некому будет мониторить VM.

### Нужно что-то устанавливать на мониторимые VM?

**НЕТ!** VM работают как обычно. Watchdog следит извне через ping и Yandex Cloud API.

### Сколько VM можно мониторить?

**Неограниченно!** Ограничение только в ресурсах watchdog сервера (каждая VM занимает ~10-20 МБ RAM).

### Можно ли мониторить VM в разных folders?

**ДА!** Каждый профиль может иметь свой folder_id.

### Как получить логи для баг-репорта?

```bash
sudo docker logs vps-watchdog > watchdog-logs.txt
cat /opt/vps-watchdog/logs/watchdog.log >> watchdog-logs.txt
```

---

## 🐛 Проблемы и решения

### Ошибка "Permission denied" для ключа

```bash
sudo chmod 600 /opt/vps-watchdog/config/sa-key.json
sudo systemctl restart vps-watchdog
```

### Ошибка "operation is in process"

Это нормально! Скрипт ждёт завершения текущей операции и попробует снова.

### VM не запускается

Проверь:
1. Правильность Instance ID в профиле
2. Наличие прав у Service Account (`compute.operator`)
3. Статус VM в веб-консоли Yandex Cloud

### Telegram не работает

Проверь:
1. Правильность Bot Token
2. Правильность Chat ID
3. Бот должен получить хотя бы одно сообщение от тебя

---

## 🤝 Участие в разработке

Баги и предложения: [GitHub Issues](https://github.com/Mastachok/ya-vps-autostart/issues)

Pull requests приветствуются! 🎉

---

## 📜 Лицензия

MIT License - делай что хочешь! 🎉

---

## 🙏 Благодарности

- [Yandex Cloud](https://cloud.yandex.ru/) за API
- [Docker](https://www.docker.com/) за контейнеризацию
- [Telegram](https://telegram.org/) за Bot API
- Всем контрибьюторам! ❤️

---

## 📞 Контакты

- 💬 Telegram: @your_username
- 🐛 Issues: [GitHub](https://github.com/Mastachok/ya-vps-autostart/issues)
- 📧 Email: your@email.com

---

<p align="center">
  <b>Сделано с ❤️ для сообщества</b>
</p>

<p align="center">
  ⭐ Поставь звезду на GitHub если проект помог! ⭐
</p>
