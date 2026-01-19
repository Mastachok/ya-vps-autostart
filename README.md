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

#### 1️⃣ Загрузи Service Account ключ (ОБЯЗАТЕЛЬНО!)
- Выбери пункт **"📤 Загрузить SA ключ"**
- Следуй инструкции на экране
- [Подробная инструкция →](docs/SERVICE_ACCOUNT_SETUP.md)

#### 2️⃣ Добавь профиль VM
- Выбери пункт **"➕ Добавить профиль (OAuth)"**
- Откроется ссылка для OAuth токена
- Скрипт автоматически найдёт все твои VM
- Выбери VM для мониторинга
- Профиль создан! ✅

#### 3️⃣ Настрой Telegram (опционально)
- Создай бота через [@BotFather](https://t.me/botfather)
- Укажи Bot Token и Chat ID
- Получи тестовое уведомление! 📱

#### 4️⃣ Запусти мониторинг

```bash
sudo systemctl start vps-watchdog
sudo docker logs -f vps-watchdog
```

**Готово!** 🎉

---

## ⚠️ ВАЖНО: Service Account ключ

### 🔑 Без SA ключа VPS Watchdog НЕ СМОЖЕТ запускать VM!

Service Account (SA) - это специальный аккаунт в Yandex Cloud который позволяет VPS Watchdog:
- ✅ Запускать упавшие VM через API
- ✅ Проверять статус операций
- ✅ Управлять виртуальными машинами

### Быстрая настройка (3 шага):

#### Шаг 1: Создай Service Account в Yandex Cloud

1. Открой [Yandex Cloud Console](https://console.cloud.yandex.ru/)
2. Выбери folder где находятся твои VM
3. Меню → **"Сервисные аккаунты"** → **"Создать"**
4. Имя: `vps-watchdog-sa`
5. Роль: **`compute.operator`** ⚠️ ОБЯЗАТЕЛЬНО!

#### Шаг 2: Скачай ключ

1. Открой созданный SA
2. Вкладка **"Ключи"** → **"Создать авторизованный ключ"**
3. **Скачай JSON файл**

#### Шаг 3: Загрузи через меню

```bash
sudo vps-watchdog
# Выбери: "📤 Загрузить SA ключ"
# Следуй инструкциям на экране
```

### 📚 Полная инструкция

👉 **[docs/SERVICE_ACCOUNT_SETUP.md](docs/SERVICE_ACCOUNT_SETUP.md)** - Подробная инструкция с примерами

---

## 🎯 Чеклист перед запуском

Убедись что выполнено:

- [ ] ✅ **Service Account создан** в Yandex Cloud
- [ ] ✅ SA имеет роль **`compute.operator`** на folder с VM
- [ ] ✅ SA ключ загружен через меню или в `/opt/vps-watchdog/config/sa-key.json`
- [ ] ✅ Добавлен хотя бы один профиль VM
- [ ] ✅ (Опционально) Настроен Telegram бот
- [ ] ✅ Сервис запущен: `sudo systemctl start vps-watchdog`

### Проверка:

```bash
# Проверь что SA ключ на месте
ls -la /opt/vps-watchdog/config/sa-key.json

# Проверь логи
sudo docker logs vps-watchdog

# Должно быть:
# ✅ Service Account авторизован
# ✅ Найдено X активных профилей
# ✅ VM мониторится
```

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

### Пример уведомления

```
🔴 VM Недоступна!

📊 Профиль: Production Server
🌐 IP: 158.160.75.118
⏰ Время: 19.01.2026 15:30:00
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
   🔑 SA ключ: настроен

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

🔑 SERVICE ACCOUNT:
  12) 📤 Загрузить SA ключ
  13) 🔍 Проверить SA ключ

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

## ❓ FAQ

### Watchdog должен быть в Yandex Cloud?

**НЕТ!** Watchdog может быть где угодно:
- ✅ Hetzner, AWS, DigitalOcean
- ✅ Домашний сервер
- ✅ Другая VM в Yandex Cloud
- ✅ VPS в любом датацентре

Главное - стабильный интернет и Docker.

### В чём разница между OAuth и Service Account?

| OAuth токен | Service Account ключ |
|-------------|---------------------|
| Для поиска VM в меню | Для запуска VM |
| Временный (истекает) | Постоянный |
| Используется интерактивно | Используется автоматически |
| ✅ Удобство добавления | ✅ Работа мониторинга |

**Оба нужны!** OAuth для удобства, SA для функционала.

### Можно ли обойтись без Service Account?

❌ **НЕТ!** Без SA ключа VPS Watchdog:
- ✅ Будет пинговать VM
- ✅ Отправлять уведомления о падении
- ❌ **НО НЕ СМОЖЕТ запускать VM!**

### Что если watchdog упадёт?

Выбирай стабильный хостинг для watchdog. Если он упадёт - некому будет мониторить VM.

### Нужно что-то устанавливать на мониторимые VM?

**НЕТ!** VM работают как обычно. Watchdog следит извне через ping и Yandex Cloud API.

### Сколько VM можно мониторить?

**Неограниченно!** Ограничение только в ресурсах watchdog сервера (каждая VM занимает ~10-20 МБ RAM).

---

## 🐛 Проблемы и решения

### "No such file: sa-key.json"

**Причина:** Service Account ключ не загружен

**Решение:**
```bash
# Через меню
sudo vps-watchdog
# Выбери: "📤 Загрузить SA ключ"

# Или вручную
sudo nano /opt/vps-watchdog/config/sa-key.json
# Вставь содержимое скачанного JSON
sudo chmod 600 /opt/vps-watchdog/config/sa-key.json
```

### "Не удалось запустить VM"

**Причина:** У SA нет прав или ключ невалидный

**Решение:**
1. Проверь что SA имеет роль `compute.operator`
2. Проверь что ключ валиден: `cat /opt/vps-watchdog/config/sa-key.json | jq .`
3. Перезапусти сервис: `sudo systemctl restart vps-watchdog`

### "Permission denied" для ключа

```bash
sudo chmod 600 /opt/vps-watchdog/config/sa-key.json
sudo chown root:root /opt/vps-watchdog/config/sa-key.json
sudo systemctl restart vps-watchdog
```

### VM не запускается после многих попыток

Отредактируй профиль:
```bash
sudo nano /opt/vps-watchdog/profiles/<profile_id>.json

# Измени:
"cooldown_minutes": 1,          # было 5
"max_start_attempts": 10,       # было 3
"check_interval": 30            # было 60
```

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

<p align="center">
  <b>Сделано с ❤️ для сообщества</b>
</p>

<p align="center">
  ⭐ Поставь звезду на GitHub если проект помог! ⭐
</p>
