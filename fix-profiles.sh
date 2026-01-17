#!/usr/bin/env bash
# Быстрое исправление проблемы с профилями VPS Watchdog

set -euo pipefail

echo "🔧 VPS Watchdog - Исправление проблемы с профилями"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Проверка root
if [[ "${EUID}" -ne 0 ]]; then
  echo "❌ Запусти через sudo"
  exit 1
fi

APP_DIR="/opt/vps-watchdog"
PROFILES_DIR="$APP_DIR/profiles"

echo "1️⃣ Проверяю структуру..."

# Создаём директорию профилей если нет
mkdir -p "$PROFILES_DIR"

echo "2️⃣ Удаляю файлы с пустыми именами..."

# Удаляем файлы профилей с пустыми/странными именами
find "$PROFILES_DIR" -type f -name ".env" -delete 2>/dev/null || true
find "$PROFILES_DIR" -type f -name ".sa-key.json" -delete 2>/dev/null || true

echo "3️⃣ Проверяю наличие default профиля..."

# Создаём default профиль если его нет
if [[ ! -f "$PROFILES_DIR/default.env" ]]; then
  echo "   Создаю default профиль..."
  cat > "$PROFILES_DIR/default.env" <<'EOF'
# ✅ Профиль по умолчанию (заполни через меню: Профили → Создать)
PROFILE_NAME=default
VM_HOST=
INSTANCE_ID=
CHECK_INTERVAL=60
PING_ATTEMPTS=5
PING_TIMEOUT=5
COOLDOWN_MINUTES=5
SA_KEY_FILE=/app/profiles/default.sa-key.json
EOF
fi

# Создаём пустой ключ
if [[ ! -f "$PROFILES_DIR/default.sa-key.json" ]]; then
  echo "   Создаю пустой файл ключа..."
  touch "$PROFILES_DIR/default.sa-key.json"
  chmod 600 "$PROFILES_DIR/default.sa-key.json"
fi

echo "4️⃣ Устанавливаю default как активный профиль..."

# Устанавливаем default как активный
echo "default" > "$APP_DIR/ACTIVE_PROFILE"

# Копируем .env
cp "$PROFILES_DIR/default.env" "$APP_DIR/.env"

echo "5️⃣ Показываю текущие профили:"
echo

# Показываем список профилей
if ls -1 "$PROFILES_DIR"/*.env >/dev/null 2>&1; then
  for f in "$PROFILES_DIR"/*.env; do
    name=$(basename "$f" .env)
    echo "   ✓ $name"
  done
else
  echo "   ✓ default (создан)"
fi

echo
echo "6️⃣ Перезапускаю сервис..."

systemctl restart vps-watchdog 2>/dev/null || {
  echo "   ⚠️  Сервис не запущен (это нормально если только установили)"
}

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Готово!"
echo
echo "Теперь запусти меню:"
echo "   sudo vps-watchdog"
echo
echo "И создай свой профиль:"
echo "   Профили → Создать профиль"
echo
