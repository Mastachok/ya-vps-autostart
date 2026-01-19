# 🔑 Настройка Service Account для VPS Watchdog

## ❓ Что такое Service Account?

**Service Account (SA)** - это специальный аккаунт в Yandex Cloud который позволяет приложениям управлять ресурсами через API.

VPS Watchdog **обязательно** нужен SA ключ для:
- ✅ Запуска упавших VM
- ✅ Проверки статуса операций
- ✅ Получения информации о VM

---

## 📋 Пошаговая инструкция

### Шаг 1: Создай Service Account

1. Открой **Yandex Cloud Console**: https://console.cloud.yandex.ru/
2. Выбери своё **облако** (Cloud)
3. Выбери **папку (Folder)** где находятся твои VM
4. В левом меню найди **"Сервисные аккаунты"** (Service Accounts)
5. Нажми **"Создать сервисный аккаунт"**

### Шаг 2: Настрой права доступа

При создании SA укажи:

```
Имя: vps-watchdog-sa
Описание: Service Account для VPS Watchdog
```

**ВАЖНО!** Назначь роль:
- ✅ `compute.operator` (рекомендуется)
- или ✅ `compute.admin` (если нужны дополнительные права)

**Не используй** `compute.viewer` - он только для чтения!

### Шаг 3: Создай авторизованный ключ

1. Открой созданный Service Account
2. Перейди на вкладку **"Ключи"**
3. Нажми **"Создать новый ключ"**
4. Выбери **"Создать авторизованный ключ"**
5. Нажми **"Создать"**
6. **СКАЧАЙ JSON файл** - он нужен только один раз!

Файл будет называться примерно так:
```
authorized_key_aje9foobar123456.json
```

---

## 📤 Загрузка ключа на сервер

### Способ 1: Через меню VPS Watchdog (ПРОЩЕ)

```bash
# Запусти меню
sudo vps-watchdog

# Выбери: "📤 Загрузить Service Account ключ"
# Вставь содержимое JSON файла
```

### Способ 2: Вручную

```bash
# 1. Создай папку конфига
sudo mkdir -p /opt/vps-watchdog/config

# 2. Создай файл ключа
sudo nano /opt/vps-watchdog/config/sa-key.json

# 3. Скопируй ВЕСЬ текст из скачанного JSON файла
# 4. Вставь в nano (правая кнопка мыши или Ctrl+Shift+V)
# 5. Сохрани: Ctrl+X, затем Y, затем Enter

# 6. Установи правильные права
sudo chmod 600 /opt/vps-watchdog/config/sa-key.json

# 7. Проверь что файл валидный
cat /opt/vps-watchdog/config/sa-key.json | jq .

# Должен показать красиво отформатированный JSON
# Если ошибка - значит JSON невалидный
```

---

## ✅ Проверка

После загрузки ключа проверь что всё работает:

```bash
# Перезапусти сервис
sudo systemctl restart vps-watchdog

# Смотри логи
sudo docker logs -f vps-watchdog

# Должно быть:
# ✅ Service Account авторизован
# ✅ VM мониторится
# ✅ При падении VM запускается
```

---

## 🔒 Безопасность

### ⚠️ ВАЖНО:

1. **Не публикуй** SA ключ в Git, форумах, чатах
2. **Храни** ключ только на сервере
3. **Права** на файл должны быть `600` (только root)
4. **Не давай** роль `compute.admin` если хватает `compute.operator`

### Файл в .gitignore:

```gitignore
# Конфиденциальные данные
config/sa-key.json
config/telegram.json
profiles/*.json
```

---

## 🐛 Частые проблемы

### Ошибка: "No such file or directory"

**Причина:** SA ключ не загружен

**Решение:**
```bash
ls -la /opt/vps-watchdog/config/sa-key.json
# Если файла нет - загрузи его по инструкции выше
```

### Ошибка: "Permission denied"

**Причина:** Неправильные права на файл

**Решение:**
```bash
sudo chmod 600 /opt/vps-watchdog/config/sa-key.json
sudo chown root:root /opt/vps-watchdog/config/sa-key.json
```

### Ошибка: "Не удалось запустить VM"

**Причина:** У SA нет прав на запуск VM

**Решение:**
1. Открой Yandex Cloud Console
2. Сервисные аккаунты → твой SA
3. Проверь роли - должна быть `compute.operator` или `compute.admin`
4. Если роли нет - добавь:
   - Нажми "Назначить роль"
   - Выбери folder с VM
   - Роль: `compute.operator`

---

## 📚 Дополнительная информация

### Где найти Service Account ID:

```bash
cat /opt/vps-watchdog/config/sa-key.json | jq -r '.service_account_id'
```

### Где найти список ролей SA:

```bash
# Через yc CLI (если установлен)
yc iam service-account list-access-bindings <SA_ID>
```

Или через веб-консоль:
1. Сервисные аккаунты → твой SA
2. Вкладка "Права доступа"

---

## 🎯 Итоговый чеклист

Перед запуском VPS Watchdog убедись что:

- [ ] Service Account создан в Yandex Cloud
- [ ] SA имеет роль `compute.operator` или `compute.admin`
- [ ] Роль назначена на **folder** где находятся VM
- [ ] Авторизованный ключ скачан (JSON файл)
- [ ] Ключ загружен в `/opt/vps-watchdog/config/sa-key.json`
- [ ] Права на файл: `600` (root:root)
- [ ] Файл валидный JSON (проверено через `jq`)
- [ ] Сервис перезапущен
- [ ] В логах нет ошибок про SA

---

**Готово!** Теперь VPS Watchdog сможет запускать твои VM! 🚀
