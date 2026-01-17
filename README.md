# 🛡️ VPS Watchdog — автозапуск ВМ (Yandex Cloud)

Автоматический мониторинг и запуск виртуальных машин в Yandex Cloud.

## 📋 Что это делает?

- **Пингует** вашу ВМ по внешнему IP
- **Автоматически запускает** ВМ через Yandex Cloud API, если она не отвечает
- **Поддерживает несколько профилей** для управления разными ВМ
- **Защита от частых перезапусков** (настраиваемый cooldown период)
- **Детальное логирование** всех действий

---

## ⚡ Быстрая установка (1 команда)

```bash
curl -fsSL https://raw.githubusercontent.com/Mastachok/ya-vps-autostart/main/install.sh | sudo bash
```

После установки запусти:

```bash
sudo vps-watchdog
```

И следуй мастеру быстрой настройки!

---

## 🎯 Требования

- Ubuntu/Debian сервер (где будет запущен watchdog)
- Docker и Docker Compose (устанавливаются автоматически)
- Yandex Cloud CLI (`yc`) — [инструкция по установке](https://cloud.yandex.ru/docs/cli/quickstart)
- Service Account с ролью `compute.operator` в Yandex Cloud

---

## 🚀 Пошаговая настройка

### 1. Установка

```bash
curl -fsSL https://raw.githubusercontent.com/Mastachok/ya-vps-autostart/main/install.sh | sudo bash
```

### 2. Запуск мастера настройки

```bash
sudo vps-watchdog
```

Выбери **"Быстрая настройка"** и следуй инструкциям.

### 3. Что понадобится?

- **VM_HOST** — внешний IP адрес твоей ВМ в Yandex Cloud
- **INSTANCE_ID** — UUID виртуальной машины (получить: `yc compute instance list`)
- **Folder ID** — ID папки в Yandex Cloud (получить: `yc config list`)

---

## 📁 Управление профилями

Watchdog поддерживает несколько профилей для управления разными ВМ.

### Создать новый профиль:

```bash
sudo vps-watchdog
# → Профили → Создать профиль
```

### Переключить активный профиль:

```bash
sudo vps-watchdog
# → Профили → Переключить активный профиль
```

### Настройки профиля:

Каждый профиль содержит:
- `VM_HOST` — IP адрес ВМ для мониторинга
- `INSTANCE_ID` — UUID ВМ в Yandex Cloud
- `CHECK_INTERVAL` — интервал проверки (секунды)
- `PING_ATTEMPTS` — количество попыток ping
- `PING_TIMEOUT` — таймаут ping (секунды)
- `COOLDOWN_MINUTES` — время ожидания между попытками запуска (минуты)

---

## 🔧 Управление сервисом

### Через меню:

```bash
sudo vps-watchdog
# → Сервис
```

### Через systemctl:

```bash
# Запустить
sudo systemctl start vps-watchdog

# Остановить
sudo systemctl stop vps-watchdog

# Перезапустить
sudo systemctl restart vps-watchdog

# Статус
sudo systemctl status vps-watchdog
```

### Просмотр логов:

```bash
sudo vps-watchdog
# → Логи watchdog

# Или напрямую:
sudo docker logs -f vps-watchdog
```

---

## 🔑 Service Account и ключи

Для работы watchdog нужен Service Account с правами `compute.operator`.

### Создание через меню (рекомендуется):

```bash
sudo vps-watchdog
# → Yandex Cloud → Создать Service Account + Key
```

### Вручную:

```bash
# 1. Создать Service Account
yc iam service-account create --name watchdog-my-vm --folder-id YOUR_FOLDER_ID

# 2. Выдать права
yc resource-manager folder add-access-binding YOUR_FOLDER_ID \
  --role compute.operator \
  --subject serviceAccount:SERVICE_ACCOUNT_ID

# 3. Создать ключ
yc iam key create \
  --service-account-id SERVICE_ACCOUNT_ID \
  --output /opt/vps-watchdog/profiles/my-profile.sa-key.json
```

---

## 📊 Мониторинг и диагностика

### Проверить статус:

```bash
sudo vps-watchdog
```

Главный экран показывает:
- Активный профиль
- Состояние сервиса
- Статус контейнера
- Доступность ВМ (ping)
- Наличие ключа доступа

### Проверить ping вручную:

```bash
sudo vps-watchdog
# → Проверить ping
```

### Посмотреть логи:

```bash
# Последние 100 строк
sudo docker logs --tail=100 vps-watchdog

# В режиме реального времени
sudo docker logs -f vps-watchdog
```

---

## 🛠️ Структура проекта

```
/opt/vps-watchdog/
├── app/                    # Docker приложение
│   ├── Dockerfile
│   ├── monitor.py         # Основной скрипт мониторинга
│   ├── yc_api.py          # Работа с Yandex Cloud API
│   └── requirements.txt
├── bin/
│   └── vps-watchdog       # CLI меню
├── profiles/              # Профили конфигурации
│   ├── default.env
│   ├── default.sa-key.json
│   └── ...
├── docker-compose.yml
└── .env                   # Активный профиль
```

---

## ❓ Частые вопросы

### Watchdog не запускает ВМ

1. Проверь логи: `sudo docker logs vps-watchdog`
2. Убедись, что Service Account создан и ключ валиден: меню → Yandex Cloud → Проверить ключ
3. Проверь права SA: должна быть роль `compute.operator`

### ВМ постоянно перезапускается

1. Увеличь `COOLDOWN_MINUTES` в профиле
2. Проверь, что ВМ действительно запускается (консоль Yandex Cloud)
3. Проверь, нет ли проблем с сетью на ВМ

### Как добавить вторую ВМ?

```bash
sudo vps-watchdog
# → Профили → Создать профиль
# → Профили → Переключить активный профиль
# → Yandex Cloud → Создать Service Account + Key
```

### Как обновить watchdog?

```bash
sudo vps-watchdog
# → Обновиться из GitHub
```

---

## 🔄 Обновление

```bash
sudo vps-watchdog
# → Обновиться из GitHub
```

Или вручную:

```bash
cd /opt/vps-watchdog
sudo git pull
sudo install -m 755 bin/vps-watchdog /usr/local/bin/vps-watchdog
sudo systemctl restart vps-watchdog
```

---

## 🗑️ Удаление

```bash
sudo vps-watchdog
# → Удалить программу
```

Или вручную:

```bash
sudo systemctl stop vps-watchdog
sudo systemctl disable vps-watchdog
sudo rm -f /etc/systemd/system/vps-watchdog.service
sudo rm -f /usr/local/bin/vps-watchdog
sudo rm -rf /opt/vps-watchdog
sudo systemctl daemon-reload
```

---

## 📝 Логи и отладка

### Уровни логирования

Watchdog пишет подробные логи:
- `INFO` — обычные операции (ping OK/DOWN, попытки запуска)
- `WARNING` — предупреждения (cooldown активен, конфигурация)
- `ERROR` — ошибки (API errors, проблемы с ключом)

### Примеры логов

```
2024-01-17 12:00:00 [INFO] ✅ VM 1.2.3.4 is UP
2024-01-17 12:01:00 [WARNING] ❌ VM 1.2.3.4 is DOWN (attempt 1)
2024-01-17 12:01:00 [INFO] 🚀 Attempting to start instance fhm...
2024-01-17 12:01:01 [INFO] Getting IAM token...
2024-01-17 12:01:02 [INFO] IAM token obtained successfully
2024-01-17 12:01:02 [INFO] Sending start command...
2024-01-17 12:01:03 [INFO] ✅ Start command sent successfully (status: STARTING)
2024-01-17 12:01:03 [INFO] ⏳ Cooldown set for 5 minutes
```

---

## 🔐 Безопасность

- Service Account ключи хранятся с правами `600` (только root)
- Контейнер работает от непривилегированного пользователя
- Все API запросы используют TLS
- Ключи не попадают в логи

---

## 📄 Лицензия

MIT License

---

## 🤝 Поддержка

Если нашёл баг или есть предложения — создай [Issue](https://github.com/Mastachok/ya-vps-autostart/issues) на GitHub.

---

## 🎉 Благодарности

Спасибо за использование VPS Watchdog!
