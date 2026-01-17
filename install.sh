#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════
# VPS Watchdog v2.0 - Установка
# ═══════════════════════════════════════════════════════════════════

APP_DIR="/opt/vps-watchdog"
BIN_PATH="/usr/local/bin/vps-watchdog"
SERVICE_PATH="/etc/systemd/system/vps-watchdog.service"
REPO_URL="https://github.com/Mastachok/ya-vps-autostart.git"
REPO_BRANCH="main"

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

success() { echo -e "${GREEN}✅ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
error() { echo -e "${RED}❌ $*${NC}"; }

# Проверка root
if [[ $EUID -ne 0 ]]; then
    error "Запусти через sudo"
    exit 1
fi

echo "═══════════════════════════════════════════════════════════════"
echo "  🛡️  VPS WATCHDOG v2.0 - Установка"
echo "═══════════════════════════════════════════════════════════════"
echo

# 1. Установка зависимостей
success "Устанавливаю зависимости..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl git jq nano

# 2. Docker
if ! command -v docker >/dev/null 2>&1; then
    warn "Устанавливаю Docker..."
    curl -fsSL https://get.docker.com | sh >/dev/null
    success "Docker установлен"
else
    success "Docker уже установлен"
fi

# 3. Docker Compose
if ! docker compose version >/dev/null 2>&1; then
    warn "Устанавливаю Docker Compose..."
    apt-get install -y -qq docker-compose-plugin
fi

if ! docker compose version >/dev/null 2>&1; then
    error "Не удалось установить Docker Compose"
    exit 1
fi

success "Docker Compose готов"

# 4. Клонирование репозитория
if [[ -d "$APP_DIR/.git" ]]; then
    success "Обновляю репозиторий..."
    git -C "$APP_DIR" fetch --all -q
    git -C "$APP_DIR" checkout "$REPO_BRANCH" -q
    git -C "$APP_DIR" pull -q
else
    success "Клонирую репозиторий..."
    rm -rf "$APP_DIR"
    git clone -q --branch "$REPO_BRANCH" "$REPO_URL" "$APP_DIR"
fi

# 5. Установка CLI меню
success "Устанавливаю CLI меню..."
install -m 755 "$APP_DIR/bin/vps-watchdog" "$BIN_PATH"

# 6. Создание структуры
mkdir -p "$APP_DIR/config"

# 7. Создание примера конфига если нет
if [[ ! -f "$APP_DIR/config/watchdog.env" ]]; then
    cat > "$APP_DIR/config/watchdog.env" <<'EOF'
# ═══════════════════════════════════════════════════════════════════
# VPS Watchdog - Конфигурация
# ═══════════════════════════════════════════════════════════════════

# IP адрес вашей VM (который пингуем)
VM_HOST=

# ID виртуальной машины в Yandex Cloud
# Получить: yc compute instance list
INSTANCE_ID=

# Путь к ключу Service Account
SA_KEY_FILE=/app/config/sa-key.json

# Настройки мониторинга
CHECK_INTERVAL=60
PING_COUNT=3
PING_TIMEOUT=5

# Защита от частых перезапусков
COOLDOWN_MINUTES=5
MAX_START_ATTEMPTS=3
EOF
fi

# 8. Создание пустого ключа
if [[ ! -f "$APP_DIR/config/sa-key.json" ]]; then
    echo "{}" > "$APP_DIR/config/sa-key.json"
    chmod 600 "$APP_DIR/config/sa-key.json"
fi

# 9. Systemd service
success "Создаю systemd сервис..."
cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=VPS Watchdog - Auto-start VM (Yandex Cloud)
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/docker compose up -d --build
ExecStop=/usr/bin/docker compose down
RemainAfterExit=yes
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable vps-watchdog.service

echo
echo "═══════════════════════════════════════════════════════════════"
success "Установка завершена!"
echo
echo "🚀 Что дальше?"
echo "   1. Запусти меню:     sudo vps-watchdog"
echo "   2. Выбери пункт 1:   Быстрая настройка"
echo "   3. Следуй инструкциям"
echo
echo "💡 Или настрой вручную:"
echo "   sudo vps-watchdog"
echo "   → пункт 2 (Настроить конфигурацию)"
echo "   → пункт 3 (Настроить ключ)"
echo
echo "📖 Документация:"
echo "   https://github.com/Mastachok/ya-vps-autostart"
echo "═══════════════════════════════════════════════════════════════"
