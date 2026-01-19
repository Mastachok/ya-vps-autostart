# 📱 НАСТРОЙКА TELEGRAM БОТА

## 🤖 Шаг 1: Создание бота

### 1.1 Открой Telegram и найди @BotFather

Напиши в поиске: `@BotFather` и открой официального бота

### 1.2 Создай нового бота

```
Отправь: /newbot
```

BotFather спросит:
```
Alright, a new bot. How are we going to call it? 
Please choose a name for your bot.
```

Введи **имя бота** (можно любое):
```
VPS Watchdog Monitor
```

### 1.3 Выбери username

BotFather попросит username (должен заканчиваться на `bot`):
```
Good. Now let's choose a username for your bot. 
It must end in `bot`. Like this, for example: TetrisBot or tetris_bot.
```

Введи username:
```
vps_watchdog_monitor_bot
```

### 1.4 Получи токен

BotFather выдаст токен:
```
Done! Congratulations on your new bot. You will find it at 
t.me/vps_watchdog_monitor_bot. You can now add a description...

Use this token to access the HTTP API:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

**Скопируй токен!** Например: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

---

## 💬 Шаг 2: Получение Chat ID

### 2.1 Напиши боту

1. Открой своего бота по ссылке из BotFather
2. Нажми **Start**
3. Отправь любое сообщение, например: `Hello`

### 2.2 Узнай свой Chat ID

Открой в браузере (замени TOKEN на свой токен):
```
https://api.telegram.org/botTOKEN/getUpdates
```

Пример:
```
https://api.telegram.org/bot1234567890:ABCdefGHIjklMNOpqrsTUVwxyz/getUpdates
```

Увидишь JSON ответ:
```json
{
  "ok": true,
  "result": [
    {
      "update_id": 123456789,
      "message": {
        "message_id": 1,
        "from": {
          "id": 987654321,  ← ЭТО ТВОЙ CHAT ID!
          "first_name": "Твоё имя"
        },
        "chat": {
          "id": 987654321,  ← ИЛИ ВОТ ТУТ
          "first_name": "Твоё имя",
          "type": "private"
        },
        "text": "Hello"
      }
    }
  ]
}
```

**Скопируй Chat ID!** Например: `987654321`

---

## ⚙️ Шаг 3: Настройка на сервере

### 3.1 Через меню vps-watchdog

```bash
vps-watchdog

# Выбери: 6) 🤖 Настроить бота
```

Введи:
- **Bot Token:** `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
- **Chat ID:** `987654321`

### 3.2 Вручную (альтернатива)

```bash
# Создай конфиг
cat > /opt/vps-watchdog/config/telegram.json << EOF
{
  "enabled": true,
  "bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
  "chat_id": "987654321"
}
EOF

# Установи права
chmod 600 /opt/vps-watchdog/config/telegram.json

# Перезапусти
systemctl restart vps-watchdog
```

---

## ✅ Шаг 4: Проверка

### 4.1 Тест уведомления

```bash
vps-watchdog

# Выбери: 7) 📤 Тест уведомления
```

Должно прийти сообщение в Telegram:
```
✅ Тест уведомления VPS Watchdog
Бот работает корректно!
```

### 4.2 Проверь логи

```bash
docker logs vps-watchdog | grep Telegram
```

Должно быть:
```
[INFO] Telegram: настроен
```

---

## 📨 Какие уведомления будут приходить

### ❌ VM упала:
```
❌ VM EyTest не отвечает
🖥️  51.250.27.80
🔄 Попытка запуска #1
```

### 🚀 VM запускается:
```
🚀 Запуск VM EyTest
📍 Instance ID: epdfv5c8r930gcm4flqj
⏱️  Ожидание старта...
```

### ✅ VM восстановлена:
```
✅ VM EyTest восстановлена
🖥️  51.250.27.80
⏱️  Downtime: 45с
```

### ⚠️ Ошибка запуска:
```
❌ Ошибка запуска VM EyTest
💬 Permission denied: insufficient permissions
```

---

## 🔒 Безопасность

⚠️ **Не делись токеном бота!** Любой с токеном может управлять ботом.

⚠️ **Храни токен в безопасности:**
```bash
chmod 600 /opt/vps-watchdog/config/telegram.json
```

⚠️ **Если токен утёк:**
1. Открой @BotFather
2. Отправь: `/mybots`
3. Выбери своего бота
4. `API Token` → `Revoke current token`
5. Получи новый токен
6. Обнови в конфиге

---

## 🎯 Готово!

Теперь будешь получать уведомления о всех событиях с VM! 🎉

**Следующий шаг:** Добавь больше VM для мониторинга через меню (пункт 2)
