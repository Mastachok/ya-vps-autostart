# 🛡️ VPS Watchdog v2.0

**Простой и надёжный автозапуск виртуальных машин в Yandex Cloud**

Следит за твоей VM и автоматически запускает её если она упала.

---

## ✨ Возможности

✅ Автоматический мониторинг VM по ping  
✅ Запуск VM через Yandex Cloud API  
✅ Защита от частых перезапусков (cooldown)  
✅ Детальное логирование  
✅ Простое меню для настройки  
✅ Работает в Docker  

---

## ⚡ Установка (1 команда)

```bash
curl -fsSL https://raw.githubusercontent.com/Mastachok/ya-vps-autostart/main/install.sh | sudo bash
```

---

## 🚀 Быстрый старт

После установки:

```bash
sudo vps-watchdog
```

Выбери **"1) Быстрая настройка"** и следуй инструкциям! 🎯

---

## 📋 Что нужно подготовить?

### Вариант 1: Автоматический сбор (рекомендуется) 🚀

Используй автоматический скрипт для сбора всех данных:

```bash
curl -fsSL https://raw.githubusercontent.com/Mastachok/ya-vps-autostart/main/bin/get-vm-data -o get-vm-data
chmod +x get-vm-data
./get-vm-data
```

**Способы авторизации в скрипте:**
- **OAuth токен** (через браузер) - самый простой! [Как получить?](docs/OAUTH_TOKEN.md)
- **yc CLI** - если уже установлен

Скрипт автоматически:
- ✅ Найдёт все твои VM
- ✅ Покажет их IP и ID
- ✅ Создаст/использует Service Account
- ✅ Создаст и сохранит ключ
- ✅ Выдаст все данные готовыми

### Вариант 2: Вручную

1. **VM_HOST** - внешний IP адрес твоей VM
2. **INSTANCE_ID** - UUID VM в Yandex Cloud  
   Получить: `yc compute instance list`
3. **yc CLI** - установленный и настроенный  
   Установка: [yandex.cloud/docs/cli](https://cloud.yandex.ru/docs/cli/quickstart)

📖 **Подробная инструкция:**
- [Где взять данные (с картинками)](docs/VISUAL_GUIDE.md)
- [Автоматический сбор данных](docs/WHERE_TO_GET_DATA.md)

---

## 🎮 Управление

### Главное меню

```bash
sudo vps-watchdog
```

Доступные команды:
- 🚀 **Быстрая настройка** - автоматическая настройка за 2 минуты
- ⚙️ **Настроить конфигурацию** - ручная настройка параметров
- 🔑 **Настроить ключ** - создание Service Account
- 🔧 **Управление сервисом** - запуск/остановка/перезапуск
- 📜 **Показать логи** - просмотр логов в реальном времени
- 📡 **Проверить ping** - тест доступности VM

### Управление через systemctl

```bash
# Запуск
sudo systemctl start vps-watchdog

# Остановка
sudo systemctl stop vps-watchdog

# Перезапуск
sudo systemctl restart vps-watchdog

# Статус
sudo systemctl status vps-watchdog

# Логи
sudo docker logs -f vps-watchdog
```

---

## ⚙️ Настройки

Все настройки в одном файле: `/opt/vps-watchdog/config/watchdog.env`

```bash
# Основное
VM_HOST=1.2.3.4                    # IP адрес VM
INSTANCE_ID=fhm...                 # ID VM в Yandex Cloud

# Мониторинг
CHECK_INTERVAL=60                  # Интервал проверки (секунды)
PING_COUNT=3                       # Количество ping
PING_TIMEOUT=5                     # Таймаут ping (секунды)

# Защита
COOLDOWN_MINUTES=5                 # Время между попытками запуска
MAX_START_ATTEMPTS=3               # Макс. попыток подряд
```

---

## 🔑 Service Account

Для работы нужен Service Account с ролью `compute.operator`.

### Создание через меню (рекомендуется):

```bash
sudo vps-watchdog
# → пункт 3 (Настроить ключ)
```

### Создание вручную:

```bash
# 1. Создать SA
yc iam service-account create --name watchdog --folder-id YOUR_FOLDER_ID

# 2. Выдать права
yc resource-manager folder add-access-binding YOUR_FOLDER_ID \
  --role compute.operator \
  --subject serviceAccount:SA_ID

# 3. Создать ключ
yc iam key create \
  --service-account-id SA_ID \
  --output /opt/vps-watchdog/config/sa-key.json
```

---

## 📊 Примеры логов

```
2026-01-17 10:00:00 [INFO] ═══════════════════════════════════════════
2026-01-17 10:00:00 [INFO] 🛡️  VPS WATCHDOG - Конфигурация
2026-01-17 10:00:00 [INFO] ═══════════════════════════════════════════
2026-01-17 10:00:00 [INFO] 🌐 VM Host:             1.2.3.4
2026-01-17 10:00:00 [INFO] 🆔 Instance ID:         fhm1234567890
2026-01-17 10:00:00 [INFO] ✅ Конфигурация валидна
2026-01-17 10:00:00 [INFO] 🚀 Запуск мониторинга...
2026-01-17 10:00:01 [INFO] ✅ VM 1.2.3.4 доступна
2026-01-17 10:01:01 [WARNING] ❌ VM 1.2.3.4 НЕ отвечает (попытка 1)
2026-01-17 10:01:01 [INFO] 🚀 Попытка #1 запустить VM...
2026-01-17 10:01:01 [INFO]    Текущий статус: STOPPED
2026-01-17 10:01:02 [INFO]    ✅ VM запускается
2026-01-17 10:01:02 [INFO] ⏳ Cooldown установлен на 5 минут
```

---

## ❓ FAQ

### VM не запускается?

1. Проверь логи: `sudo docker logs vps-watchdog`
2. Проверь ключ: меню → пункт 3 → проверить ключ
3. Убедись что SA имеет роль `compute.operator`

### Где взять INSTANCE_ID?

```bash
yc compute instance list
```

### Как изменить интервал проверки?

```bash
sudo vps-watchdog
# → пункт 2 (Настроить конфигурацию)
# → измени CHECK_INTERVAL
```

### VM постоянно перезапускается?

Увеличь `COOLDOWN_MINUTES` в конфигурации.

---

## 🔄 Обновление

```bash
cd /opt/vps-watchdog
sudo git pull
sudo install -m 755 bin/vps-watchdog /usr/local/bin/vps-watchdog
sudo systemctl restart vps-watchdog
```

---

## 🗑️ Удаление

```bash
sudo systemctl stop vps-watchdog
sudo systemctl disable vps-watchdog
sudo rm -f /etc/systemd/system/vps-watchdog.service
sudo rm -f /usr/local/bin/vps-watchdog
sudo rm -rf /opt/vps-watchdog
sudo systemctl daemon-reload
```

---

## 📝 Структура проекта

```
/opt/vps-watchdog/
├── app/
│   ├── monitor.py          # Основной скрипт мониторинга
│   └── Dockerfile
├── bin/
│   └── vps-watchdog        # CLI меню
├── config/
│   ├── watchdog.env        # Конфигурация
│   └── sa-key.json         # Ключ Service Account
└── docker-compose.yml
```

---

## 🤝 Поддержка

Нашёл баг? Есть предложение?  
Создай [Issue на GitHub](https://github.com/Mastachok/ya-vps-autostart/issues)

---

## 📄 Лицензия

MIT License

---

**Made with ❤️ for simple VM management**
