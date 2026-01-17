#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/vps-watchdog"
BIN_PATH="/usr/local/bin/vps-watchdog"
SERVICE_PATH="/etc/systemd/system/vps-watchdog.service"

REPO_URL="https://github.com/Mastachok/ya-vps-autostart.git"
REPO_BRANCH="main"

say() { echo -e "✅ $*"; }
warn() { echo -e "⚠️  $*"; }
err() { echo -e "❌ $*" >&2; }
need_root() { [[ "${EUID}" -eq 0 ]] || { err "Запусти через sudo"; exit 1; }; }

need_root

echo "🛡️ VPS Watchdog - Установка"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# 1) Базовые пакеты
say "Устанавливаю зависимости..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
  ca-certificates curl git jq whiptail

# 2) Docker (если нет)
if ! command -v docker >/dev/null 2>&1; then
  warn "Docker не найден — устанавливаю Docker..."
  curl -fsSL https://get.docker.com | sh
  say "Docker установлен."
else
  say "Docker уже установлен."
fi

# 3) Проверка docker compose
if ! docker compose version >/dev/null 2>&1; then
  warn "docker compose не найден. На Ubuntu обычно ставится пакетом docker-compose-plugin."
  warn "Пробую установить docker-compose-plugin..."
  apt-get install -y docker-compose-plugin || true
fi

if ! docker compose version >/dev/null 2>&1; then
  err "Не удалось установить docker compose. Установи вручную docker-compose-plugin и повтори."
  exit 1
fi

say "Docker Compose готов."

# 4) Клонируем/обновляем репо
if [[ -d "$APP_DIR/.git" ]]; then
  say "Обновляю репозиторий в $APP_DIR..."
  git -C "$APP_DIR" fetch --all
  git -C "$APP_DIR" checkout "$REPO_BRANCH"
  git -C "$APP_DIR" pull
else
  say "Клонирую репозиторий в $APP_DIR..."
  rm -rf "$APP_DIR"
  git clone --branch "$REPO_BRANCH" "$REPO_URL" "$APP_DIR"
fi

# 5) Ставим бинарь меню
say "Устанавливаю команду меню: vps-watchdog"
install -m 755 "$APP_DIR/bin/vps-watchdog" "$BIN_PATH"

# 6) Профили: создаём пустой default (без мусорных значений)
mkdir -p "$APP_DIR/profiles"

if [[ ! -f "$APP_DIR/ACTIVE_PROFILE" ]]; then
  echo "default" > "$APP_DIR/ACTIVE_PROFILE"
fi

DEFAULT_ENV="$APP_DIR/profiles/default.env"
DEFAULT_KEY="$APP_DIR/profiles/default.sa-key.json"

if [[ ! -f "$DEFAULT_ENV" ]]; then
  cat > "$DEFAULT_ENV" <<'EOF'
# ✅ Профиль по умолчанию (заполни через меню: Профили → Создать)
# VM_HOST — внешний IP ВМ (кого пингуем)
# INSTANCE_ID — UUID ВМ в Yandex Cloud (кого запускать)
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

# пустой файл ключа (появится после создания SA+Key)
if [[ ! -f "$DEFAULT_KEY" ]]; then
  : > "$DEFAULT_KEY"
  chmod 600 "$DEFAULT_KEY" || true
fi

# применим env для активного профиля
cp -f "$DEFAULT_ENV" "$APP_DIR/.env"

# 7) systemd service
say "Создаю systemd сервис..."
cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=VPS Watchdog (Yandex Cloud)
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
systemctl restart vps-watchdog.service

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
say "Установка завершена!"
echo
echo "👉 Запусти мастер настройки:"
echo "   sudo vps-watchdog"
echo
echo "📖 Что делать дальше:"
echo "   1. Запусти: sudo vps-watchdog"
echo "   2. Выбери 'Быстрая настройка'"
echo "   3. Следуй инструкциям мастера"
echo
